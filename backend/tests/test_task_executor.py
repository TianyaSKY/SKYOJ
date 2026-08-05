"""任务执行骨架 run_job 与 finalize_dataset 下沉测试。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.domain.async_job import CreateAsyncJobParams
from app.messaging.queues import JUDGE_QUEUE
from app.messaging.task_names import JUDGE_SUBMISSION_TASK
from app.repositories.dataset_repository import DatasetRepository
from app.services.async_job_service import AsyncJobService
from app.services.dataset_service import DatasetService
from app.tasks import base as tasks_base
from app.tasks.base import run_job


def make_session():
    """创建独立的内存数据库会话。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)()


def seed_job(db, payload=None, max_attempts=3):
    """在独立库里创建一条待执行任务。"""
    service = AsyncJobService.from_session(db)
    job = service.enqueue(
        CreateAsyncJobParams(
            task_name=JUDGE_SUBMISSION_TASK,
            queue=JUDGE_QUEUE,
            payload=payload or {"submission_id": 1},
            dedupe_key=None,
            max_attempts=max_attempts,
        )
    )
    return service, job


def use_test_session(engine, monkeypatch):
    """让 run_job 使用与种子数据相同的库。"""
    monkeypatch.setattr(tasks_base, "SessionLocal", sessionmaker(bind=engine))


def test_run_job_success_path(monkeypatch):
    engine, db = make_session()
    try:
        service, job = seed_job(db)
        use_test_session(engine, monkeypatch)

        seen = {}

        def handler(session, payload):
            seen["payload"] = payload
            return {"ok": True}

        result = run_job(job.id, task_name=JUDGE_SUBMISSION_TASK, handler=handler)

        assert result == {"ok": True}
        assert seen["payload"] == {"submission_id": 1}
        assert service._repository.get_by_id(job.id).status == "succeeded"
    finally:
        db.close()
        engine.dispose()


def test_run_job_exception_path_retries_and_calls_on_failed(monkeypatch):
    engine, db = make_session()
    try:
        service, job = seed_job(db)
        use_test_session(engine, monkeypatch)

        failed = []

        def handler(session, payload):
            raise RuntimeError("boom")

        result = run_job(
            job.id,
            task_name=JUDGE_SUBMISSION_TASK,
            handler=handler,
            on_failed=lambda payload, outcome: failed.append((payload, outcome)),
        )

        assert result is None
        assert failed == [({"submission_id": 1}, "boom")]
        model = service._repository.get_by_id(job.id)
        assert model.status == "pending"  # 仍有重试次数，任务回到待处理
        assert model.attempts == 1
        assert model.last_error == "boom"
    finally:
        db.close()
        engine.dispose()


class _PermanentError(Exception):
    """模拟 _PermanentTestDataError 场景。"""


def test_run_job_permanent_error_marks_failed_without_retry(monkeypatch):
    engine, db = make_session()
    try:
        service, job = seed_job(db)
        use_test_session(engine, monkeypatch)

        failed = []

        def handler(session, payload):
            raise _PermanentError("bad input")

        result = run_job(
            job.id,
            task_name=JUDGE_SUBMISSION_TASK,
            handler=handler,
            on_failed=lambda payload, outcome: failed.append((payload, outcome)),
            permanent_errors=(_PermanentError,),
        )

        assert result is None
        assert failed == [({"submission_id": 1}, "bad input")]
        model = service._repository.get_by_id(job.id)
        assert model.status == "failed"
        assert model.finished_at is not None
    finally:
        db.close()
        engine.dispose()


class _BusinessFailed:
    status = "failed"


def test_run_job_business_failure_completes_job_and_calls_on_failed(monkeypatch):
    engine, db = make_session()
    try:
        service, job = seed_job(db)
        use_test_session(engine, monkeypatch)

        failed = []

        def handler(session, payload):
            return _BusinessFailed()

        result = run_job(
            job.id,
            task_name=JUDGE_SUBMISSION_TASK,
            handler=handler,
            on_failed=lambda payload, outcome: failed.append((payload, outcome)),
        )

        assert result is not None
        assert result.status == "failed"
        assert len(failed) == 1
        assert failed[0][0] == {"submission_id": 1}
        assert failed[0][1].status == "failed"
        assert service._repository.get_by_id(job.id).status == "succeeded"
    finally:
        db.close()
        engine.dispose()


def test_run_job_duplicate_delivery_skips_handler(monkeypatch):
    engine, db = make_session()
    try:
        service, job = seed_job(db)
        use_test_session(engine, monkeypatch)

        # 已被另一个 worker 领取，租约仍有效
        assert service.start_job(job.id, lease_seconds=600) is not None

        called = []

        def handler(session, payload):
            called.append(payload)
            return {"ok": True}

        result = run_job(job.id, task_name=JUDGE_SUBMISSION_TASK, handler=handler)

        assert result is None
        assert called == []
    finally:
        db.close()
        engine.dispose()


class FakeStorageClient:
    def __init__(self, exists=False):
        self.calls = []
        self._exists = exists

    def exists(self, file_path):
        return self._exists

    def finalize(self, temporary_path, file_path, dataset_id):
        self.calls.append(("finalize", temporary_path, file_path, dataset_id))
        return 2048, "abc123"


def test_finalize_dataset_success_marks_ready():
    engine, db = make_session()
    try:
        dataset = DatasetRepository(db).create(
            name="d",
            description="",
            file_path="uploads/datasets/x.csv",
            file_size="",
            uploader_id=1,
            temp_path="tmp/x.pending",
            status="pending",
        )
        storage = FakeStorageClient()
        service = DatasetService(
            DatasetRepository(db), storage, AsyncJobService.from_session(db)
        )

        service.finalize_dataset(dataset.id)

        assert storage.calls == [
            ("finalize", "tmp/x.pending", "uploads/datasets/x.csv", dataset.id)
        ]
        updated = DatasetRepository(db).get_by_id(dataset.id)
        assert updated.status == "ready"
        assert updated.file_hash == "abc123"
        assert updated.file_size == "2.00 KB"
        assert updated.temp_path is None
    finally:
        db.close()
        engine.dispose()


def test_finalize_dataset_already_ready_returns_without_finalize():
    engine, db = make_session()
    try:
        dataset = DatasetRepository(db).create(
            name="d",
            description="",
            file_path="uploads/datasets/x.csv",
            file_size="1 KB",
            uploader_id=1,
            temp_path=None,
            status="ready",
        )
        storage = FakeStorageClient(exists=True)
        service = DatasetService(
            DatasetRepository(db), storage, AsyncJobService.from_session(db)
        )

        service.finalize_dataset(dataset.id)

        assert storage.calls == []
        assert DatasetRepository(db).get_by_id(dataset.id).status == "ready"
    finally:
        db.close()
        engine.dispose()


class FailingStorageClient:
    def exists(self, file_path):
        return False

    def finalize(self, temporary_path, file_path, dataset_id):
        raise OSError("disk full")


def test_finalize_dataset_failure_marks_failed_and_raises():
    engine, db = make_session()
    try:
        dataset = DatasetRepository(db).create(
            name="d",
            description="",
            file_path="uploads/datasets/x.csv",
            file_size="",
            uploader_id=1,
            temp_path="tmp/x.pending",
            status="pending",
        )
        service = DatasetService(
            DatasetRepository(db), FailingStorageClient(), AsyncJobService.from_session(db)
        )

        with pytest.raises(OSError, match="disk full"):
            service.finalize_dataset(dataset.id)

        updated = DatasetRepository(db).get_by_id(dataset.id)
        assert updated.status == "failed"
        assert updated.error_message == "disk full"
    finally:
        db.close()
        engine.dispose()

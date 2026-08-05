"""异步任务状态、租约与直接投递回归测试。"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.domain.async_job import CreateAsyncJobParams
from app.messaging.celery_app import celery_app
from app.messaging.queues import JUDGE_QUEUE
from app.messaging.task_names import JUDGE_SUBMISSION_TASK
from app.models.async_job import AsyncJob
from app.services.async_job_service import AsyncJobService


def make_session():
    """创建独立的内存数据库会话。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)()


def capture_send_task(monkeypatch):
    """拦截 celery send_task，记录投递调用。"""
    sent = []
    monkeypatch.setattr(
        celery_app,
        "send_task",
        lambda *args, **kwargs: sent.append((args, kwargs)),
    )
    return sent


def make_params(**overrides):
    values = {
        "task_name": JUDGE_SUBMISSION_TASK,
        "queue": JUDGE_QUEUE,
        "payload": {"submission_id": 7},
        "dedupe_key": "judge-submission:7",
    }
    values.update(overrides)
    return CreateAsyncJobParams(**values)


def test_enqueue_publishes_once_and_dedupe_skips_resend(monkeypatch):
    engine, db = make_session()
    try:
        service = AsyncJobService.from_session(db)
        sent = capture_send_task(monkeypatch)

        first = service.enqueue(make_params())
        duplicate = service.enqueue(make_params())

        assert duplicate.id == first.id
        assert len(sent) == 1
        assert sent[0][0] == (JUDGE_SUBMISSION_TASK,)
        assert sent[0][1]["args"] == [first.id]
        assert sent[0][1]["queue"] == JUDGE_QUEUE
        assert sent[0][1]["task_id"] == f"async-job-{first.id}-0"
        assert db.query(AsyncJob).count() == 1
    finally:
        db.close()
        engine.dispose()


def test_enqueue_publish_failure_deletes_job_and_raises(monkeypatch):
    engine, db = make_session()
    try:
        service = AsyncJobService.from_session(db)

        def boom(*args, **kwargs):
            raise ConnectionError("broker unreachable")

        monkeypatch.setattr(celery_app, "send_task", boom)

        with pytest.raises(ConnectionError):
            service.enqueue(
                make_params(payload={"submission_id": 8}, dedupe_key="judge-submission:8")
            )

        # 投递失败撤销任务记录，dedupe 键不会命中僵尸任务
        assert db.query(AsyncJob).count() == 0
    finally:
        db.close()
        engine.dispose()


def test_fail_job_with_retry_republishes(monkeypatch):
    engine, db = make_session()
    try:
        service = AsyncJobService.from_session(db)
        job = service.enqueue(
            make_params(payload={"submission_id": 9}, dedupe_key=None)
        )
        assert service.start_job(job.id, lease_seconds=60) is not None
        sent = capture_send_task(monkeypatch)

        result = service.fail_job(job.id, "boom")

        assert result.status == "pending"  # 仍有重试次数
        assert len(sent) == 1
        assert sent[0][1]["args"] == [job.id]
        # attempts 已在 claim 时 +1，重投递使用新 task_id，且延迟到 available_at
        assert sent[0][1]["task_id"] == f"async-job-{job.id}-1"
        assert sent[0][1]["countdown"] == 1  # 2 ** (attempts - 1) = 1 秒退避
    finally:
        db.close()
        engine.dispose()


def test_fail_job_without_retry_does_not_republish(monkeypatch):
    engine, db = make_session()
    try:
        service = AsyncJobService.from_session(db)
        job = service.enqueue(
            make_params(payload={"submission_id": 10}, dedupe_key=None, max_attempts=1)
        )
        assert service.start_job(job.id, lease_seconds=60) is not None
        sent = capture_send_task(monkeypatch)

        result = service.fail_job(job.id, "boom")

        assert result.status == "failed"
        assert sent == []
    finally:
        db.close()
        engine.dispose()


def test_job_lease_expiry_recovery_republishes(monkeypatch):
    engine, db = make_session()
    try:
        service = AsyncJobService.from_session(db)
        job = service.enqueue(
            make_params(payload={"submission_id": 11}, dedupe_key=None)
        )
        assert service.start_job(job.id, lease_seconds=60).attempts == 1

        model = service._repository.get_by_id(job.id)
        model.lease_until = (
            datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
        )
        db.commit()
        sent = capture_send_task(monkeypatch)

        assert service.recover_expired_jobs() == 1

        recovered = service._repository.get_by_id(job.id)
        assert recovered.status == "pending"
        assert recovered.lease_until is None
        assert len(sent) == 1
        assert sent[0][1]["args"] == [job.id]
    finally:
        db.close()
        engine.dispose()


def test_recovery_republishes_stuck_pending_jobs(monkeypatch):
    """消息丢失/提前到达被拒后，pending 且已到 available_at 的任务应被重新投递。"""
    engine, db = make_session()
    try:
        service = AsyncJobService.from_session(db)
        job = service.enqueue(
            make_params(payload={"submission_id": 12}, dedupe_key=None)
        )
        # 模拟消息丢失：任务仍 pending 且早已可领取，但从未被消费
        model = service._repository.get_by_id(job.id)
        model.available_at = (
            datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=60)
        )
        db.commit()
        sent = capture_send_task(monkeypatch)

        assert service.recover_expired_jobs() == 1
        assert len(sent) == 1
        assert sent[0][1]["args"] == [job.id]
        assert service._repository.get_by_id(job.id).status == "pending"
    finally:
        db.close()
        engine.dispose()

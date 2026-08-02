"""异步任务状态、Outbox 与租约回归测试。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.domain.async_job import (
    CreateAsyncJobParams,
    JUDGE_QUEUE,
    JUDGE_SUBMISSION_TASK,
)
from app.messaging.celery_app import celery_app
from app.models.async_job import AsyncJobOutbox
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


def test_enqueue_is_idempotent_and_outbox_contains_only_job_id(monkeypatch):
    engine, db = make_session()
    try:
        service = AsyncJobService.from_session(db)
        params = CreateAsyncJobParams(
            task_name=JUDGE_SUBMISSION_TASK,
            queue=JUDGE_QUEUE,
            payload={"submission_id": 7},
            dedupe_key="judge-submission:7",
        )
        first = service.enqueue(params)
        duplicate = service.enqueue(params)

        assert duplicate.id == first.id
        outbox = db.query(AsyncJobOutbox).one()
        assert outbox.job.payload == '{"submission_id": 7}'

        sent = []
        monkeypatch.setattr(
            celery_app,
            "send_task",
            lambda *args, **kwargs: sent.append((args, kwargs)),
        )
        assert service.publish_pending_jobs() == 1
        assert sent[0][0] == (JUDGE_SUBMISSION_TASK,)
        assert sent[0][1]["args"] == [first.id]
        assert service.publish_pending_jobs() == 0
    finally:
        db.close()
        engine.dispose()


def test_job_lease_and_expiry_recovery_requeue_outbox():
    engine, db = make_session()
    try:
        service = AsyncJobService.from_session(db)
        job = service.enqueue(
            CreateAsyncJobParams(
                task_name=JUDGE_SUBMISSION_TASK,
                queue=JUDGE_QUEUE,
                payload={"submission_id": 8},
                dedupe_key="judge-submission:8",
            )
        )
        assert service.start_job(job.id, lease_seconds=60).attempts == 1

        model = service._repository.get_by_id(job.id)
        model.lease_until = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
        db.commit()

        assert service.recover_expired_jobs() == 1
        recovered = service._repository.get_by_id(job.id)
        assert recovered.status == "pending"
        assert recovered.lease_until is None
        assert recovered.outbox.status == "pending"
    finally:
        db.close()
        engine.dispose()

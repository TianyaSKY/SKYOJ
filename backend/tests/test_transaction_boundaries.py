"""验证跨仓储的原子提交、回滚与发布前的持久化。"""

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from app.persistence.database import Base
from app.persistence.jobs import AiDraft, AiDraftRepository, AsyncJobRepository
from app.persistence.problem import Problem, ProblemRepository
from app.persistence.unit_of_work import UnitOfWork
from app.services.ai_draft import TASK_PROBLEM_GENERATION, AiDraftService
from app.services.async_job import AsyncJobService, CreateAsyncJobParams
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_apply_draft_rolls_back_problem_if_consumption_fails(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        draft = AiDraft(
            user_id=1,
            task_type=TASK_PROBLEM_GENERATION,
            status="success",
            title="草稿",
            result_payload=json.dumps({"title": "题目", "content": "内容"}),
        )
        db.add(draft)
        db.commit()
        draft_id = draft.id
        repo = AiDraftRepository(db)
        service = AiDraftService(
            repo, ProblemRepository(db), MagicMock(), uow=UnitOfWork(db)
        )

        def fail(_):
            raise RuntimeError("consumption failed")

        monkeypatch.setattr(repo, "mark_consumed", fail)
        with pytest.raises(RuntimeError, match="consumption failed"):
            service.apply_problem_draft(1, draft_id, requester_role="teacher")
        assert db.query(Problem).count() == 0
        assert db.get(AiDraft, draft_id).consumed_at is None
        monkeypatch.undo()
        result = service.apply_problem_draft(1, draft_id, requester_role="teacher")
        with Session(engine) as observer:
            assert observer.get(Problem, result.problem_id).title == "题目"
            assert observer.get(AiDraft, draft_id).consumed_at is not None


def test_enqueue_is_committed_before_publish(tmp_path, monkeypatch):
    from app.persistence.jobs import AsyncJob

    engine = create_engine(f"sqlite:///{tmp_path / 'queue.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        service = AsyncJobService(AsyncJobRepository(db), uow=UnitOfWork(db))
        published = []

        def publish(job):
            with Session(engine) as observer:
                assert observer.get(AsyncJob, job.id) is not None
            published.append(job.id)

        monkeypatch.setattr(service, "_publish", publish)
        job = service.enqueue(
            CreateAsyncJobParams(
                task_name="test", queue="judge", payload={}, dedupe_key=None
            )
        )
        assert published == [job.id]


def test_worker_can_record_failure_after_database_flush_error(monkeypatch):
    from app.persistence.jobs import AsyncJob
    from app.tasks import base
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(base, "SessionLocal", sessions)
    with sessions() as seed:
        service = AsyncJobService(AsyncJobRepository(seed), uow=UnitOfWork(seed))
        job = service.enqueue(
            CreateAsyncJobParams(
                task_name="test", queue="judge", payload={}, dedupe_key="duplicate"
            )
        )
        job_id = job.id

    def fail_flush(db, payload):
        db.add(
            AsyncJob(
                task_name="test",
                queue="judge",
                payload="{}",
                dedupe_key="duplicate",
                available_at=datetime.now(),
            )
        )
        db.flush()

    assert base.run_job(job_id, task_name="test", handler=fail_flush) is None
    with sessions() as observer:
        stored = observer.get(AsyncJob, job_id)
        assert stored.status == "pending"
        assert stored.attempts == 1
        assert "UNIQUE constraint failed" in stored.last_error

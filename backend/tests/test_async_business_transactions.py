"""业务记录和异步任务原子保存，以及判题后业务数据的一致性。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from app.clients.dataset_storage_client import DatasetStorageClient
from app.persistence.database import Base
from app.persistence.dataset import Dataset, DatasetRepository
from app.persistence.jobs import (
    AiDraft,
    AiDraftRepository,
    AsyncJob,
    AsyncJobRepository,
)
from app.persistence.problem import Problem, ProblemRepository
from app.persistence.submission import (
    DebugRun,
    DebugRunRepository,
    Submission,
    SubmissionRepository,
)
from app.persistence.unit_of_work import UnitOfWork
from app.persistence.user import User, WrongBook, WrongBookRepository
from app.services import judge
from app.services.ai_draft import AiDraftService, SubmitProblemGenerationParams
from app.services.async_job import AsyncJobService
from app.services.dataset import DatasetService, UploadDatasetParams
from app.services.debug import CreateDebugRunParams, DebugService
from app.services.plagiarism import PlagiarismService
from app.services.submission import SubmissionService, SubmitParams
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def business_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'business.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, username="student", password_hash="test", role="student"))
        db.add(
            Problem(id=1, title="题目", content="内容", type="acm", language="python")
        )
        db.commit()
        yield db, engine
    engine.dispose()


def business_action(kind, db, jobs, uow, tmp_path):
    if kind == "submission":
        service = SubmissionService(SubmissionRepository(db), jobs, uow=uow)
        return Submission, lambda: service.submit(
            SubmitParams(1, 1, "print(1)", "python"), requester_role="student"
        )
    if kind == "debug":
        service = DebugService(DebugRunRepository(db), jobs, uow=uow)
        return DebugRun, lambda: service.create(
            CreateDebugRunParams(1, 1, "python", "print(1)"), requester_role="student"
        )
    if kind == "dataset":
        storage = DatasetStorageClient(upload_folder=str(tmp_path / "uploads"))
        service = DatasetService(DatasetRepository(db), storage, jobs, uow=uow)
        return Dataset, lambda: service.upload_dataset(
            UploadDatasetParams("teacher", 1, "data.csv", b"x\n1")
        )
    service = AiDraftService(
        AiDraftRepository(db),
        ProblemRepository(db),
        jobs,
        llm_client=MagicMock(),
        uow=uow,
    )
    return AiDraft, lambda: service.submit_problem_generation(
        SubmitProblemGenerationParams(1, "排序", "简单", "teacher")
    )


@pytest.mark.parametrize("kind", ["submission", "debug", "dataset", "draft"])
def test_task_creation_failure_rolls_back_business_record(
    kind, business_database, tmp_path, monkeypatch
):
    db, engine = business_database
    uow = UnitOfWork(db)
    repo = AsyncJobRepository(db)
    jobs = AsyncJobService(repo, uow=uow)
    model, action = business_action(kind, db, jobs, uow, tmp_path)

    def fail(**kwargs):
        raise RuntimeError("job creation failed")

    monkeypatch.setattr(repo, "create", fail)
    with pytest.raises(RuntimeError, match="job creation failed"):
        action()
    with Session(engine) as observer:
        assert observer.query(model).count() == 0
        assert observer.query(AsyncJob).count() == 0
    assert not list((tmp_path / "uploads").rglob("*.pending-*"))


@pytest.mark.parametrize("kind", ["submission", "debug", "dataset", "draft"])
def test_broker_failure_preserves_business_and_recoverable_task(
    kind, business_database, tmp_path, monkeypatch
):
    db, engine = business_database
    uow = UnitOfWork(db)
    jobs = AsyncJobService(AsyncJobRepository(db), uow=uow)
    model, action = business_action(kind, db, jobs, uow, tmp_path)
    published = []

    def fail_publish(job):
        # 投递时业务记录与任务都必须对其他会话可见。
        with Session(engine) as observer:
            assert observer.query(model).count() == 1
            assert observer.get(AsyncJob, job.id).status == "pending"
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(jobs, "_publish", fail_publish)
    action()
    with Session(engine) as observer:
        assert observer.query(model).count() == 1
        job = observer.query(AsyncJob).one()
        assert job.status == "pending"
        if kind == "dataset":
            assert Path(observer.query(Dataset).one().temp_path).read_bytes() == b"x\n1"
    monkeypatch.setattr(jobs, "_publish", lambda job: published.append(job.id))
    assert jobs.recover_expired_jobs() == 1
    assert published == [job.id]


def test_wrong_book_failure_rolls_back_judge_result(business_database, monkeypatch):
    db, engine = business_database
    submission = SubmissionRepository(db).create(1, 1, None, "python", "print(1)")
    db.commit()
    monkeypatch.setattr(
        judge, "run_acm_judge", lambda *a, **kw: ("Wrong Answer", 0, "WA", [])
    )

    def fail(*args, **kwargs):
        raise RuntimeError("wrong book failed")

    monkeypatch.setattr(WrongBookRepository, "upsert", fail)
    with pytest.raises(RuntimeError, match="wrong book failed"):
        judge.judge_submission(submission.id, db)
    with Session(engine) as observer:
        assert observer.get(Submission, submission.id).status == "Pending"
        assert observer.query(WrongBook).count() == 0


def test_judge_commits_result_and_wrong_book_together(business_database, monkeypatch):
    db, engine = business_database
    submission = SubmissionRepository(db).create(1, 1, None, "python", "print(1)")
    db.commit()
    monkeypatch.setattr(
        judge, "run_acm_judge", lambda *a, **kw: ("Wrong Answer", 0, "WA", [])
    )
    judge.judge_submission(submission.id, db)
    with Session(engine) as observer:
        assert observer.get(Submission, submission.id).status == "Wrong Answer"
        assert observer.query(WrongBook).one().submission_id == submission.id


def test_new_accepted_submissions_each_schedule_scan(business_database, monkeypatch):
    db, _ = business_database
    monkeypatch.setattr(AsyncJobService, "_publish", lambda *a, **kw: None)
    judge._enqueue_plagiarism_scan(db, 1, 10)
    first = db.query(AsyncJob).one()
    first.status = "succeeded"
    db.commit()
    judge._enqueue_plagiarism_scan(db, 1, 11)
    judge._enqueue_plagiarism_scan(db, 1, 11)
    assert {job.dedupe_key for job in db.query(AsyncJob)} == {
        "plagiarism-scan:1:10",
        "plagiarism-scan:1:11",
    }


def test_manual_scans_can_repeat_after_completion(business_database, monkeypatch):
    db, _ = business_database
    uow = UnitOfWork(db)
    jobs = AsyncJobService(AsyncJobRepository(db), uow=uow)
    monkeypatch.setattr(jobs, "_publish", lambda job: None)
    service = PlagiarismService(
        MagicMock(), SubmissionRepository(db), job_service=jobs, uow=uow
    )
    first = service.trigger_manual_scan(1, "teacher")
    jobs.complete_job(first)
    second = service.trigger_manual_scan(1, "teacher")
    assert second != first

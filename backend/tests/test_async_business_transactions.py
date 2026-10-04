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

@pytest.mark.parametrize('failure_stage', ['submission', 'job', 'commit', 'broker'])
def test_csv_attachment_follows_submission_transaction(
    failure_stage, business_database, tmp_path, monkeypatch,
):
    from app.clients.submission_storage_client import SubmissionStorageClient

    db, engine = business_database
    db.get(Problem, 1).type = 'kaggle'
    db.commit()
    storage = SubmissionStorageClient(str(tmp_path / 'submissions'))
    previous = Path(storage.save(1, 1, 'answer.csv', b'previous'))
    uow = UnitOfWork(db)
    repo = SubmissionRepository(db)
    job_repo = AsyncJobRepository(db)
    jobs = AsyncJobService(job_repo, uow=uow)
    service = SubmissionService(repo, jobs, storage, uow=uow)

    def fail(*args, **kwargs):
        raise RuntimeError(f'{failure_stage} failed')

    if failure_stage == 'submission':
        monkeypatch.setattr(repo, 'create', fail)
    elif failure_stage == 'job':
        monkeypatch.setattr(job_repo, 'create', fail)
    elif failure_stage == 'commit':
        monkeypatch.setattr(db, 'commit', fail)
    else:
        monkeypatch.setattr(jobs, '_publish', fail)
    params = SubmitParams(1, 1, '__file_upload__', 'csv', is_file_upload=True,
                          filename='answer.csv', file_content=b'current')
    if failure_stage == 'broker':
        result = service.submit(params, requester_role='student')
        with Session(engine) as observer:
            submission = observer.get(Submission, result.submission_id)
            assert Path(submission.code_path).read_bytes() == b'current'
            assert observer.query(AsyncJob).one().status == 'pending'
    else:
        with pytest.raises(RuntimeError, match=f'{failure_stage} failed'):
            service.submit(params, requester_role='student')
        with Session(engine) as observer:
            assert observer.query(Submission).count() == 0
            assert observer.query(AsyncJob).count() == 0
        assert list((tmp_path / 'submissions').rglob('answer.csv')) == [previous]
        assert list((tmp_path / 'submissions').iterdir()) == [previous.parent]
    assert previous.read_bytes() == b'previous'

@pytest.mark.parametrize('kind', ['like', 'favorite'])
@pytest.mark.parametrize('initially_active', [False, True])
def test_overlapping_reaction_toggles_are_serialized(kind, initially_active, business_database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.persistence.community import ProblemCommunityRepository, ProblemSolution, ProblemSolutionLike, ProblemSolutionFavorite
    from app.services.community import SolutionService, CreateSolutionParams

    db, engine = business_database
    repo = ProblemCommunityRepository(db)
    service = SolutionService(repo, uow=UnitOfWork(db))
    created = service.create(CreateSolutionParams(1, 1, '题解', '正文'))
    solution_id = created.id
    if initially_active:
        (service.toggle_like if kind == 'like' else service.toggle_favorite)(solution_id, 1)
    barrier = Barrier(2)

    def toggle():
        with Session(engine) as session:
            repository = ProblemCommunityRepository(session)
            original = repository.get_solution_for_update

            def synchronized_lock(identifier):
                barrier.wait(timeout=5)
                return original(identifier)

            repository.get_solution_for_update = synchronized_lock
            worker = SolutionService(repository, uow=UnitOfWork(session))
            result = (worker.toggle_like if kind == 'like' else worker.toggle_favorite)(solution_id, 1)
            return result.liked if kind == 'like' else result.favorited

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(toggle) for _ in range(2)]
        assert sorted(future.result(timeout=10) for future in futures) == [False, True]
    with Session(engine) as observer:
        current = observer.get(ProblemSolution, solution_id)
        model = ProblemSolutionLike if kind == 'like' else ProblemSolutionFavorite
        assert observer.query(model).count() == int(initially_active)
        assert (current.vote_count if kind == 'like' else current.favorite_count) == int(initially_active)


@pytest.mark.parametrize('initially_reviewed', [False, True])
def test_overlapping_review_toggles_preserve_both_operations(initially_reviewed, business_database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.core.time import utcnow
    from app.services.wrong_book import WrongBookService

    db, engine = business_database
    entry = WrongBook(user_id=1, problem_id=1, first_wrong_at=utcnow(), latest_wrong_at=utcnow(), reviewed=initially_reviewed)
    db.add(entry)
    db.commit()
    entry_id = entry.id
    barrier = Barrier(2)

    def toggle():
        with Session(engine) as session:
            # 保留 ORM 对象，确保两个会话都从相同的旧状态发起操作。
            cached = session.get(WrongBook, entry_id)
            assert cached.reviewed == initially_reviewed
            repository = WrongBookRepository(session)
            original = repository.toggle_reviewed

            def overlapping_toggle(identifier):
                barrier.wait(timeout=5)
                return original(identifier)

            repository.toggle_reviewed = overlapping_toggle
            service = WrongBookService(repository, uow=UnitOfWork(session))
            return service.toggle_reviewed(entry_id, 1).reviewed

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(toggle) for _ in range(2)]
        assert sorted(future.result(timeout=10) for future in futures) == [False, True]
    with Session(engine) as observer:
        assert observer.get(WrongBook, entry_id).reviewed == initially_reviewed


def test_concurrent_exam_problem_additions_do_not_create_duplicates(business_database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from datetime import datetime, timedelta
    from app.core.errors import InvalidStateError
    from app.persistence.exam import ExamProblem, ExamRepository
    from app.services.exam import ExamService, CreateExamParams, AddExamProblemParams

    db, engine = business_database
    now = datetime(2090, 1, 1)
    created = ExamService(ExamRepository(db), uow=UnitOfWork(db)).create_exam('teacher',
        CreateExamParams(title='并发添加', description='', start_time=now,
                         end_time=now + timedelta(hours=1), created_by=1))
    barrier = Barrier(2)

    def add():
        with Session(engine) as session:
            repo = ExamRepository(session)
            lock = repo.lock_exam

            def synchronized_lock(exam_id):
                barrier.wait(timeout=5)
                return lock(exam_id)

            repo.lock_exam = synchronized_lock
            service = ExamService(repo, uow=UnitOfWork(session))
            try:
                service.add_problem('teacher', created.id, AddExamProblemParams(1, 'A', 100))
            except InvalidStateError:
                return 'duplicate'
            return 'added'

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(add) for _ in range(2)]
        assert sorted(future.result(timeout=10) for future in futures) == ['added', 'duplicate']
    with Session(engine) as check:
        assert check.query(ExamProblem).filter_by(exam_id=created.id, problem_id=1).count() == 1


def test_concurrent_partial_exam_updates_preserve_each_other_fields(business_database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from datetime import datetime, timedelta
    from app.persistence.exam import Exam, ExamRepository
    from app.services.exam import ExamService, CreateExamParams, UpdateExamParams

    db, engine = business_database
    now = datetime(2090, 1, 1)
    created = ExamService(ExamRepository(db), uow=UnitOfWork(db)).create_exam('teacher',
        CreateExamParams(title='原始标题', description='原始说明', start_time=now,
                         end_time=now + timedelta(hours=1), created_by=1))
    barrier = Barrier(2)

    def save(params):
        with Session(engine) as session:
            cached = session.get(Exam, created.id)
            assert cached.title == '原始标题'
            repo = ExamRepository(session)
            lock = repo.lock_exam

            def synchronized_lock(exam_id):
                barrier.wait(timeout=5)
                return lock(exam_id)

            repo.lock_exam = synchronized_lock
            return ExamService(repo, uow=UnitOfWork(session)).update_exam('teacher', created.id, params)

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(save, UpdateExamParams(title='新的标题')),
                   workers.submit(save, UpdateExamParams(description='新的说明'))]
        for future in futures:
            future.result(timeout=10)
    with Session(engine) as check:
        row = check.get(Exam, created.id)
        assert row.title == '新的标题'
        assert row.description == '新的说明'

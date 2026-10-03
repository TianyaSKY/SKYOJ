"""持久化收拢回归：独立快照、社区事务和错题本访问控制。"""

from dataclasses import fields, is_dataclass
from unittest.mock import MagicMock

import pytest
from app.core.errors import PermissionDeniedError, ResourceNotFoundError
from app.persistence.community import (
    ProblemCommunityRepository,
    ProblemSolution,
    ProblemSolutionLike,
)
from app.persistence.database import Base
from app.persistence.jobs import AiDraftRepository
from app.persistence.problem import ProblemRepository
from app.persistence.submission import SubmissionRepository
from app.persistence.unit_of_work import UnitOfWork
from app.persistence.user import UserRepository, WrongBook, WrongBookRepository
from app.services.community import (
    AttachTagParams,
    CreateCommentParams,
    CreateSolutionParams,
    CreateTagParams,
    SolutionService,
    TagService,
    UpdateSolutionParams,
)
from app.services.wrong_book import WrongBookService
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db_session():
    """真实事务测试使用独立数据库；提交后的种子不受后续回滚影响。"""
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def assert_has_no_orm(value):
    """包括关联字段在内，快照不得包含 SQLAlchemy 实例。"""
    assert inspect(value, raiseerr=False) is None
    if is_dataclass(value):
        for field in fields(value):
            assert_has_no_orm(getattr(value, field.name))
    elif isinstance(value, dict):
        for item in value.values():
            assert_has_no_orm(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            assert_has_no_orm(item)


def test_repository_records_remain_usable_after_session_detach(
    db_session, student_user, sample_problem
):
    repository = SubmissionRepository(db_session)
    submission = repository.create(
        student_user.id, sample_problem.id, None, "python", "print(1)"
    )
    problem = ProblemRepository(db_session).get_by_id(sample_problem.id)
    user = UserRepository(db_session).get_by_id(student_user.id)
    draft = AiDraftRepository(db_session).create(
        user_id=student_user.id,
        task_type="problem_generation",
        title="草稿",
        request_payload={},
    )
    community = ProblemCommunityRepository(db_session)
    solution = community.create_solution(
        problem_id=sample_problem.id,
        author_id=student_user.id,
        title="题解",
        content="解法",
        language="python",
    )
    snapshots = [submission, problem, user, draft, solution]
    assert_has_no_orm(snapshots)
    db_session.expunge_all()
    assert submission.user.username == user.username
    assert submission.problem.title == problem.title
    assert solution.author.username == user.username
    assert draft.request_payload == "{}"


def test_community_mutations_persist_snapshots_and_counts(
    db_session, student_user, teacher_user, sample_problem
):
    repo = ProblemCommunityRepository(db_session)
    service = SolutionService(repo, uow=UnitOfWork(db_session))
    created = service.create(
        CreateSolutionParams(
            sample_problem.id, student_user.id, "题解", "旧解法", "python"
        )
    )
    updated = service.update(
        UpdateSolutionParams(
            solution_id=created.id,
            requester_id=teacher_user.id,
            requester_role="teacher",
            content="新解法",
            is_official=True,
        )
    )
    assert updated.content == "新解法"
    assert updated.is_official
    assert service.get(created.id, student_user.id).view_count == 1
    assert service.toggle_like(created.id, teacher_user.id).vote_count == 1
    assert service.toggle_favorite(created.id, teacher_user.id).favorited
    viewed = service.get(created.id, teacher_user.id)
    assert viewed.liked_by_me and viewed.favorited_by_me
    assert viewed.favorite_count == 1
    assert service.toggle_like(created.id, teacher_user.id).vote_count == 0
    assert not service.toggle_favorite(created.id, teacher_user.id).favorited
    comment = service.add_comment(
        CreateCommentParams(created.id, teacher_user.id, "评论")
    )
    assert comment.username == teacher_user.username
    assert repo.get_solution_by_id(created.id).comment_count == 1
    service.delete_comment(comment.id, teacher_user.id, "teacher")
    assert repo.get_solution_by_id(created.id).comment_count == 0
    service.hide(created.id, student_user.id, "student")
    with pytest.raises(ResourceNotFoundError):
        service.get(created.id, student_user.id)


def test_like_and_counter_roll_back_together(
    db_session, student_user, sample_problem, monkeypatch
):
    repo = ProblemCommunityRepository(db_session)
    service = SolutionService(repo, uow=UnitOfWork(db_session))
    created = service.create(
        CreateSolutionParams(sample_problem.id, student_user.id, "题解", "解法")
    )
    monkeypatch.setattr(
        repo, "save_solution", MagicMock(side_effect=RuntimeError("计数写入失败"))
    )
    with pytest.raises(RuntimeError, match="计数写入失败"):
        service.toggle_like(created.id, student_user.id)
    assert db_session.query(ProblemSolutionLike).count() == 0
    assert db_session.get(ProblemSolution, created.id).vote_count == 0


def test_tag_approval_persists_and_problem_filter_uses_injected_repository(
    db_session, teacher_user, sample_problem
):
    repo = ProblemCommunityRepository(db_session)
    service = TagService(repo, uow=UnitOfWork(db_session))
    tag = service.create(CreateTagParams("teacher", "arrays", "数组"))
    service.attach(AttachTagParams(sample_problem.id, tag.id, False, "student"))
    assert repo.list_problem_ids_by_tag(tag.id) == []
    service.attach(AttachTagParams(sample_problem.id, tag.id, True, "teacher"))
    assert repo.list_problem_ids_by_tag(tag.id) == [sample_problem.id]
    assert service.list_for_problem(sample_problem.id)[0].id == tag.id
    from app.services.problem import ProblemService

    problem_service = ProblemService(
        ProblemRepository(db_session), MagicMock(), repo, uow=UnitOfWork(db_session)
    )
    assert [
        item.id for item in problem_service.list_problems("teacher", tag_id=tag.id)
    ] == [sample_problem.id]
    service.detach(sample_problem.id, tag.id, "teacher")
    assert service.list_for_problem(sample_problem.id) == []


def test_wrong_book_checks_owner_before_writing_and_updates_stats(
    db_session, student_user, teacher_user, sample_problem
):
    submission = SubmissionRepository(db_session).create(
        student_user.id, sample_problem.id, None, "python", "print(1)"
    )
    repo = WrongBookRepository(db_session)
    service = WrongBookService(repo, uow=UnitOfWork(db_session))
    service.on_judge_complete(
        student_user.id, sample_problem.id, submission.id, "Wrong Answer"
    )
    items, total = service.list_for_user(student_user.id)
    assert total == 1 and items[0].problem_title == sample_problem.title
    with pytest.raises(PermissionDeniedError):
        service.toggle_reviewed(items[0].id, teacher_user.id)
    assert not db_session.get(WrongBook, items[0].id).reviewed
    assert service.toggle_reviewed(items[0].id, student_user.id).reviewed
    assert service.get_stats(student_user.id).reviewed == 1
    service.on_judge_complete(
        student_user.id, sample_problem.id, submission.id, "Accepted"
    )
    assert service.get_stats(student_user.id).accepted == 1


def test_repeated_plagiarism_report_updates_existing_row(
    db_session, student_user, sample_problem
):
    from app.persistence.submission import PlagiarismRepository

    submissions = SubmissionRepository(db_session)
    first = submissions.create(student_user.id, sample_problem.id, None, "python", "a")
    second = submissions.create(student_user.id, sample_problem.id, None, "python", "b")
    reports = PlagiarismRepository(db_session)
    original = reports.upsert_report(
        sample_problem.id, first.id, second.id, 0.5, [], "pending"
    )
    updated = reports.upsert_report(
        sample_problem.id, second.id, first.id, 0.9, [], "reviewed"
    )
    assert original.id == updated.id
    assert reports.get_by_id(original.id).similarity_score == 0.9
    assert reports.get_by_id(original.id).status == "reviewed"


def test_failed_request_rolls_back_and_closes_its_session(db_session, monkeypatch):
    from app.persistence import database
    from app.persistence.problem import Problem

    created_sessions = []

    def session_factory():
        session = Session(db_session.get_bind())
        created_sessions.append(session)
        return session

    monkeypatch.setattr(database, "SessionLocal", session_factory)
    dependency = database.get_db()
    request_session = next(dependency)
    record = ProblemRepository(request_session).create(
        title="未完成请求",
        content="内容",
        language="python",
        problem_type="acm",
        time_limit=1000,
        memory_limit=128,
        template_code="",
    )
    with pytest.raises(ValueError, match="业务失败"):
        dependency.throw(ValueError("业务失败"))
    assert db_session.get(Problem, record.id) is None
    assert not created_sessions[0].in_transaction()

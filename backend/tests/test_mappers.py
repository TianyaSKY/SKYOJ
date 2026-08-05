"""ORM → 领域映射层测试：字段映射、改名、跨实体依赖与 AuthContext 去 ORM。"""

from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.domain.auth import AuthUserInfo
from app.domain.async_job import AsyncJobResult
from app.domain.dataset import DatasetDetail, DatasetListItem
from app.domain.exam import ExamDetail, ExamListItem
from app.domain.problem import ProblemDetail, ProblemListItem
from app.domain.submission import SubmissionDetail, SubmissionListItem
from app.domain.user import UserProfile, UserSubmissionItem
from app.mappers import (
    from_ai_draft_orm,
    from_async_job_orm,
    from_dataset_detail_orm,
    from_dataset_orm,
    from_exam_detail_orm,
    from_exam_orm,
    from_problem_orm,
    from_submission_detail_orm,
    from_submission_orm,
    from_user_orm,
    from_user_submission_orm,
)
from app.models.user import User
from app.utils.auth_tools import encode_auth_token, get_current_auth

NOW = datetime(2026, 1, 1, 9, 0, 0)


def test_from_problem_orm_list_item_and_detail():
    problem = SimpleNamespace(
        id=1,
        title="求和",
        content="计算 a+b",
        type="acm",
        language="python",
        time_limit=1000,
        memory_limit=128,
        template_code=None,
        test_case_path="uploads/problems/1",
        created_at=NOW,
    )

    item = from_problem_orm(problem)
    detail = from_problem_orm(problem, with_content=True)

    assert isinstance(item, ProblemListItem)
    assert item.problem_type == "acm"  # ORM 的 type → 领域的 problem_type
    assert detail.problem_type == "acm"
    assert detail.content == "计算 a+b"
    assert detail.template_code == ""  # None → 空串
    assert detail.test_case_path == "uploads/problems/1"


def test_from_submission_orm_uses_user_username():
    submission = SimpleNamespace(
        id=3,
        user_id=1,
        user=SimpleNamespace(username="alice"),
        problem_id=2,
        exam_id=None,
        status="Accepted",
        score=100.0,
        language="python",
        created_at=NOW,
    )

    item = from_submission_orm(submission)

    assert isinstance(item, SubmissionListItem)
    assert item.username == "alice"


def test_from_submission_detail_orm_renames_code_and_log():
    submission = SimpleNamespace(
        id=3,
        status="Wrong Answer",
        score=0.0,
        output_log="case 1 failed",
        code_content="print(1)",
        language="python",
        exam_id=1,
        created_at=NOW,
    )

    detail = from_submission_detail_orm(submission)

    assert isinstance(detail, SubmissionDetail)
    assert detail.code == "print(1)"
    assert detail.log == "case 1 failed"


def test_from_user_orm():
    user = SimpleNamespace(id=1, username="alice", role="teacher", avatar="a.png")

    profile = from_user_orm(user)

    assert isinstance(profile, UserProfile)
    assert profile.id == 1
    assert profile.role == "teacher"
    assert profile.avatar == "a.png"


def test_from_user_submission_orm_uses_problem_title():
    submission = SimpleNamespace(
        id=5,
        problem_id=2,
        problem=SimpleNamespace(title="求和"),
        status="Accepted",
        score=100.0,
        language="cpp",
        created_at=NOW,
        exam_id=None,
    )

    item = from_user_submission_orm(submission)

    assert isinstance(item, UserSubmissionItem)
    assert item.problem_title == "求和"


def test_from_user_submission_orm_unknown_problem():
    submission = SimpleNamespace(
        id=5,
        problem_id=2,
        problem=None,
        status="Pending",
        score=0.0,
        language="python",
        created_at=NOW,
        exam_id=None,
    )

    assert from_user_submission_orm(submission).problem_title == "Unknown"


def test_from_dataset_orm_list_and_detail():
    dataset = SimpleNamespace(
        id=7,
        name="iris.csv",
        description=None,
        file_path="uploads/datasets/iris.csv",
        file_size="2.00 KB",
        uploader_id=1,
        uploader=SimpleNamespace(username="alice"),
        created_at=NOW,
        status="ready",
    )

    item = from_dataset_orm(dataset)
    detail = from_dataset_detail_orm(dataset)

    assert isinstance(item, DatasetListItem)
    assert item.uploader == "alice"
    assert item.download_url == "/api/datasets/7/download"
    assert isinstance(detail, DatasetDetail)
    assert detail.file_path == "uploads/datasets/iris.csv"
    assert detail.description == ""


def test_from_exam_orm_counts_and_password():
    exam = SimpleNamespace(
        id=1,
        title="期中",
        description=None,
        start_time=NOW,
        end_time=NOW,
        is_visible=True,
        created_by=1,
        password="hashed",
    )

    item = from_exam_orm(exam, problem_count=2, submission_count=5)

    assert isinstance(item, ExamListItem)
    assert item.problem_count == 2
    assert item.submission_count == 5
    assert item.has_password is True


def test_from_exam_detail_orm_problems_with_titles():
    exam = SimpleNamespace(
        id=1,
        title="期中",
        description="d",
        start_time=NOW,
        end_time=NOW,
        is_visible=True,
        created_by=1,
        password=None,
    )
    problems = [
        SimpleNamespace(problem_id=1, display_id="A", score=100, problem=SimpleNamespace(title="求和")),
        SimpleNamespace(problem_id=2, display_id="B", score=50, problem=SimpleNamespace(title="排序")),
    ]

    detail = from_exam_detail_orm(exam, problems)

    assert isinstance(detail, ExamDetail)
    assert detail.has_password is False
    assert [item.title for item in detail.problems] == ["求和", "排序"]


def test_from_ai_draft_orm_summary_and_detail():
    draft = SimpleNamespace(
        id=9,
        task_type="problem_generation",
        status="success",
        title="出题中 · x",
        problem_id=3,
        request_payload='{"background": "b"}',
        result_payload='{"title": "T"}',
        error_message=None,
        created_at=NOW,
        updated_at=NOW,
        consumed_at=None,
    )

    summary = from_ai_draft_orm(draft)
    detail = from_ai_draft_orm(draft, detail=True)

    assert summary.title == "出题中 · x"
    assert detail.request_payload == {"background": "b"}
    assert detail.result_payload == {"title": "T"}


def test_from_async_job_orm():
    job = SimpleNamespace(
        id=11,
        task_name="skyoj.tasks.judge_submission",
        queue="judge",
        status="running",
        attempts=1,
        max_attempts=3,
        lease_until=NOW,
        created_at=NOW,
        updated_at=NOW,
    )

    result = from_async_job_orm(job)

    assert isinstance(result, AsyncJobResult)
    assert result.status == "running"
    assert result.attempts == 1


def test_get_current_auth_returns_auth_user_info():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        user = User(username="alice", password_hash="x", role="student")
        db.add(user)
        db.commit()
        token = encode_auth_token(user.id, user.role)

        context = get_current_auth(authorization=f"Bearer {token}", db=db)

        assert isinstance(context.user, AuthUserInfo)
        assert context.user.id == user.id
        assert context.user.username == "alice"
        assert context.user.role == "student"
    finally:
        db.close()
        engine.dispose()

"""考试可见性、密码与入场会话回归测试。"""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.domain.errors import PermissionDeniedError, ResourceNotFoundError
from app.domain.exam import EnterExamParams
from app.services.exam_service import ExamService
from app.utils.time import utcnow


class FakeExamRepository:
    """用于验证考试访问控制的内存仓储。"""

    def __init__(self, exam, problems=None) -> None:
        self.exam = exam
        self.problems = problems or []

    def get_by_id(self, exam_id: int):
        return self.exam if exam_id == self.exam.id else None

    def list_problems(self, exam_id: int, ordered: bool = False):
        del ordered
        return self.problems if exam_id == self.exam.id else []

    def list_submissions(self, exam_id: int, problem_ids=None):
        del exam_id, problem_ids
        return []

    def count_problems(self, exam_id: int) -> int:
        del exam_id
        return len(self.problems)

    def count_submissions(self, exam_id: int) -> int:
        del exam_id
        return 0


def _exam(*, visible: bool, password: str | None = None):
    now = utcnow()
    return SimpleNamespace(
        id=8,
        title="期末考",
        description="",
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        contest_type="icpc",
        freeze_minutes=None,
        is_visible=visible,
        created_by=1,
        password=password,
    )


def _problem():
    return SimpleNamespace(
        problem_id=3,
        display_id="A",
        score=100,
        problem=SimpleNamespace(title="A+B"),
    )


def test_hidden_exam_is_not_discoverable_to_students() -> None:
    service = ExamService(FakeExamRepository(_exam(visible=False), [_problem()]))

    with pytest.raises(ResourceNotFoundError):
        service.get_detail(8, "student", -1)
    with pytest.raises(ResourceNotFoundError):
        service.enter_exam("student", 2, -1, EnterExamParams(8, None))
    with pytest.raises(ResourceNotFoundError):
        service.rank(8, "student", -1)


def test_password_exam_hides_problems_until_entered() -> None:
    hashed = ExamService._hash_password("secret")
    service = ExamService(FakeExamRepository(_exam(visible=True, password=hashed), [_problem()]))

    preview = service.get_detail(8, "student", -1)
    assert preview.problems == []
    assert preview.has_password is True

    with pytest.raises(PermissionDeniedError):
        service.rank(8, "student", -1)

    exam_id = service.enter_exam("student", 2, -1, EnterExamParams(8, "secret"))
    detail = service.get_detail(8, "student", exam_id)
    assert [item.problem_id for item in detail.problems] == [3]


def test_teacher_can_read_hidden_exam_detail() -> None:
    service = ExamService(FakeExamRepository(_exam(visible=False), [_problem()]))
    detail = service.get_detail(8, "teacher", -1)
    assert [item.problem_id for item in detail.problems] == [3]

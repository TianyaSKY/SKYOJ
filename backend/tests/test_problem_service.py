from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.core.errors import (
    AuthenticationError,
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.services.auth import AuthService, LoginParams, RegisterParams
from app.services.problem import (
    CreateProblemParams,
    PaginatedProblems,
    ProblemService,
    UpdateProblemParams,
)
from app.services.problem import TestCaseSummary as ProblemTestCaseSummary


class FakeProblemRepository:
    """用于验证题目服务的内存仓储。"""

    def __init__(self) -> None:
        self.unit_of_work = MagicMock()
        self.items = []
        self.next_id = 1
        # master 的标签过滤会无条件构造 ProblemCommunityRepository(_db)
        self._db = None

    def create(self, **kwargs):
        problem_type = kwargs.pop("problem_type")
        problem = SimpleNamespace(
            id=self.next_id,
            type=problem_type,
            test_case_path=None,
            created_at=None,
            **kwargs,
        )
        self.next_id += 1
        self.items.append(problem)
        return problem

    def get_by_id(self, problem_id: int):
        return next((item for item in self.items if item.id == problem_id), None)

    def list_all(self, page=None, page_size=None, *, filters=None):
        items = list(reversed(self.items))
        if filters and filters.visible_ids is not None:
            items = [item for item in items if item.id in filters.visible_ids]
        if page is None or page_size is None:
            return items, None
        start = (page - 1) * page_size
        return items[start : start + page_size], len(items)

    def update(self, problem):
        return problem

    def delete(self, problem) -> None:
        self.items.remove(problem)


class FakeTestCaseStorage:
    """内存假测试用例存储：仅 1、3 号题目已有测试用例。"""

    def list_problem_ids_with_test_cases(self):
        return frozenset({1, 3})

    def has_test_cases(self, problem_id: int) -> bool:
        return problem_id in {1, 3}

    def summarize(self, problem_id: int) -> ProblemTestCaseSummary:
        if problem_id in {1, 3}:
            return ProblemTestCaseSummary(
                status="ready",
                total_count=2,
                valid_count=2,
                invalid_count=0,
                file_count=4,
                total_size=20,
                ignored_files=[],
                cases=[],
            )
        return ProblemTestCaseSummary(
            status="empty",
            total_count=0,
            valid_count=0,
            invalid_count=0,
            file_count=0,
            total_size=0,
            ignored_files=[],
            cases=[],
        )


def _service_with_three_problems() -> ProblemService:
    service = ProblemService(
        FakeProblemRepository(),
        test_case_storage=FakeTestCaseStorage(),
        uow=MagicMock(),
    )
    for title in ("A", "B", "C"):
        service.create_problem(
            "teacher",
            CreateProblemParams(
                title=title,
                content="内容",
                language="python",
                problem_type="acm",
            ),
        )
    return service


def test_problem_service_student_list_filters_out_problems_without_test_cases() -> None:
    service = _service_with_three_problems()

    visible = service.list_problems("student")

    assert {item.id for item in visible} == {1, 3}


def test_problem_service_student_pagination_total_is_filtered_count() -> None:
    service = _service_with_three_problems()

    paginated = service.list_problems("student", page=1, page_size=1)

    assert isinstance(paginated, PaginatedProblems)
    assert paginated.total == 2
    assert [item.id for item in paginated.problems] == [3]


def test_problem_service_teacher_list_includes_all_problems() -> None:
    service = _service_with_three_problems()

    visible = service.list_problems("teacher")

    assert {item.id for item in visible} == {1, 2, 3}
    status_by_id = {item.id: item for item in visible}
    assert status_by_id[1].test_case_status == "ready"
    assert status_by_id[1].test_case_count == 2
    assert status_by_id[2].test_case_status == "empty"


def test_problem_service_test_case_summary_requires_teacher_and_problem() -> None:
    service = _service_with_three_problems()

    with pytest.raises(PermissionDeniedError):
        service.get_test_case_summary("student", 1)
    with pytest.raises(ResourceNotFoundError):
        service.get_test_case_summary("teacher", 999)

    summary = service.get_test_case_summary("teacher", 1)
    assert summary.status == "ready"
    assert summary.valid_count == 2


def test_problem_service_create_update_and_paginate() -> None:
    service = ProblemService(FakeProblemRepository(), uow=MagicMock())
    created = service.create_problem(
        "teacher",
        CreateProblemParams(
            title="A",
            content="题目内容",
            language="python",
            problem_type="acm",
        ),
    )
    service.create_problem(
        "teacher",
        CreateProblemParams(
            title="B",
            content="另一个题目",
            language="cpp",
            problem_type="oop",
        ),
    )

    updated = service.update_problem(
        "teacher",
        created.id,
        UpdateProblemParams(title="更新后的题目", time_limit=2000),
    )
    paginated = service.list_problems("teacher", page=1, page_size=1)

    assert updated.title == "更新后的题目"
    assert updated.time_limit == 2000
    assert isinstance(paginated, PaginatedProblems)
    assert paginated.total == 2
    assert [item.title for item in paginated.problems] == ["B"]


def test_problem_service_raises_for_unknown_problem() -> None:
    service = ProblemService(FakeProblemRepository(), uow=MagicMock())

    with pytest.raises(ResourceNotFoundError):
        service.get_problem(999)


def test_auth_service_registers_public_student_and_logs_in() -> None:
    repository = FakeUserRepository()
    service = AuthService(
        user_repository=repository,
        password_hasher=lambda password: f"hashed:{password}",
        password_checker=lambda password_hash, password: (
            password_hash == f"hashed:{password}"
        ),
        token_encoder=lambda user_id, role: f"token:{user_id}:{role}",
        uow=MagicMock(),
    )

    registered = service.register(RegisterParams("student", "secret"))
    logged_in = service.login(LoginParams("student", "secret"))

    assert registered.username == "student"
    assert logged_in.token == "token:1:student"
    assert logged_in.user.role == "student"


def test_auth_service_rejects_duplicate_and_invalid_credentials() -> None:
    repository = FakeUserRepository()
    service = AuthService(
        user_repository=repository,
        password_hasher=lambda password: password,
        password_checker=lambda password_hash, password: password_hash == password,
        token_encoder=lambda user_id, role: "token",
        uow=MagicMock(),
    )
    service.register(RegisterParams("student", "secret"))

    with pytest.raises(InvalidStateError):
        service.register(RegisterParams("student", "secret"))
    with pytest.raises(AuthenticationError):
        service.login(LoginParams("student", "incorrect"))


class FakeUserRepository:
    """用于验证认证服务的内存仓储。"""

    def __init__(self) -> None:
        self.unit_of_work = MagicMock()
        self.items = []

    def get_by_username(self, username: str):
        return next((item for item in self.items if item.username == username), None)

    def create(self, username: str, password_hash: str, role: str):
        user = SimpleNamespace(
            id=len(self.items) + 1,
            username=username,
            password_hash=password_hash,
            role=role,
        )
        self.items.append(user)
        return user

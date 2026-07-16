from types import SimpleNamespace

import pytest

from app.domain.errors import ResourceNotFoundError
from app.domain.problem import CreateProblemParams, PaginatedProblems, UpdateProblemParams
from app.services.problem_service import ProblemService
from app.services.auth_service import AuthService
from app.domain.auth import LoginParams, RegisterParams
from app.domain.errors import AuthenticationError, InvalidStateError


class FakeProblemRepository:
    """用于验证题目服务的内存仓储。"""

    def __init__(self) -> None:
        self.items = []
        self.next_id = 1

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

    def list(self, page=None, page_size=None):
        items = list(reversed(self.items))
        if page is None or page_size is None:
            return items, None
        start = (page - 1) * page_size
        return items[start : start + page_size], len(items)

    def update(self, problem):
        return problem

    def delete(self, problem) -> None:
        self.items.remove(problem)


def test_problem_service_create_update_and_paginate() -> None:
    service = ProblemService(FakeProblemRepository())
    created = service.create_problem(
        "teacher",
        CreateProblemParams(
            title="A",
            content="题目内容",
            language="python",
            problem_type="acm",
        )
    )
    service.create_problem(
        "teacher",
        CreateProblemParams(
            title="B",
            content="另一个题目",
            language="cpp",
            problem_type="oop",
        )
    )

    updated = service.update_problem(
        "teacher",
        created.id,
        UpdateProblemParams(title="更新后的题目", time_limit=2000),
    )
    paginated = service.list_problems(page=1, page_size=1)

    assert updated.title == "更新后的题目"
    assert updated.time_limit == 2000
    assert isinstance(paginated, PaginatedProblems)
    assert paginated.total == 2
    assert [item.title for item in paginated.problems] == ["B"]


def test_problem_service_raises_for_unknown_problem() -> None:
    service = ProblemService(FakeProblemRepository())

    with pytest.raises(ResourceNotFoundError):
        service.get_problem(999)


def test_auth_service_registers_and_logs_in() -> None:
    repository = FakeUserRepository()
    service = AuthService(
        user_repository=repository,
        password_hasher=lambda password: f"hashed:{password}",
        password_checker=lambda password_hash, password: password_hash == f"hashed:{password}",
        token_encoder=lambda user_id, role: f"token:{user_id}:{role}",
    )

    registered = service.register(RegisterParams("teacher", "secret", "teacher"))
    logged_in = service.login(LoginParams("teacher", "secret"))

    assert registered.username == "teacher"
    assert logged_in.token == "token:1:teacher"
    assert logged_in.user.role == "teacher"


def test_auth_service_rejects_duplicate_and_invalid_credentials() -> None:
    repository = FakeUserRepository()
    service = AuthService(
        user_repository=repository,
        password_hasher=lambda password: password,
        password_checker=lambda password_hash, password: password_hash == password,
        token_encoder=lambda user_id, role: "token",
    )
    service.register(RegisterParams("student", "secret"))

    with pytest.raises(InvalidStateError):
        service.register(RegisterParams("student", "secret"))
    with pytest.raises(AuthenticationError):
        service.login(LoginParams("student", "incorrect"))


class FakeUserRepository:
    """用于验证认证服务的内存仓储。"""

    def __init__(self) -> None:
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

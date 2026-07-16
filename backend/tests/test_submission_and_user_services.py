from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.domain.errors import PermissionDeniedError, ResourceNotFoundError
from app.domain.submission import SubmitParams
from app.domain.user import UploadAvatarParams
from app.services.submission_service import SubmissionService
from app.services.user_service import UserService


class FakeSubmissionRepository:
    """用于验证提交服务的内存仓储。"""

    def __init__(self) -> None:
        self.problem = SimpleNamespace(id=7, type="acm")
        self.created = []

    def get_problem(self, problem_id: int):
        return self.problem if problem_id == 7 else None

    def get_active_exam(self, exam_id: int, now: datetime):
        return SimpleNamespace(id=exam_id) if exam_id == 5 else None

    def create(self, user_id, problem_id, exam_id, language, code):
        item = SimpleNamespace(
            id=len(self.created) + 1,
            user_id=user_id,
            problem_id=problem_id,
            exam_id=exam_id,
            language=language,
            code_content=code,
            status="Pending",
            score=0.0,
            output_log=None,
            created_at=datetime.now(UTC),
            user=SimpleNamespace(username="student"),
        )
        self.created.append(item)
        return item

    def get_by_id(self, submission_id: int):
        return next((item for item in self.created if item.id == submission_id), None)


class FakeQueue:
    """记录判题任务。"""

    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, *args) -> None:
        self.calls.append(args)


class FakeSubmissionStorage:
    """返回确定性的附件路径。"""

    def save(self, user_id, problem_id, filename, content) -> str:
        return f"uploads/submissions/{user_id}_{problem_id}_{filename}"


def test_submission_service_stores_uploaded_file_and_enqueues_judge() -> None:
    repository = FakeSubmissionRepository()
    queue = FakeQueue()
    service = SubmissionService(repository, queue, FakeSubmissionStorage())

    result = service.submit(
        SubmitParams(
            user_id=3,
            problem_id=7,
            language="csv",
            code="__file_upload__",
            exam_id=5,
            is_file_upload=True,
            filename="answer.csv",
            file_content=b"id,value\n1,2\n",
        )
    )

    assert result.submission_id == 1
    assert result.exam_id == 5
    assert repository.created[0].code_content.endswith("3_7_answer.csv")
    assert queue.calls and queue.calls[0][3].endswith("3_7_answer.csv")


def test_submission_service_rejects_unknown_problem() -> None:
    service = SubmissionService(FakeSubmissionRepository(), FakeQueue())

    with pytest.raises(ResourceNotFoundError):
        service.submit(SubmitParams(1, 99, "code", "python"))


class FakeUserRepository:
    """用于验证用户服务的内存仓储。"""

    def __init__(self) -> None:
        self.user = SimpleNamespace(id=1, username="teacher", role="teacher", avatar=None)

    def list_all(self):
        return [self.user]

    def get_by_id(self, user_id: int):
        return self.user if user_id == 1 else None

    def update_avatar(self, user, avatar: str):
        user.avatar = avatar
        return user

    def list_submissions(self, user_id: int):
        return []


class FakeAvatarStorage:
    """记录头像保存请求。"""

    def save(self, filename: str, content: bytes) -> str:
        assert content == b"png"
        return "/api/user/avatars/avatar.png"

    def get_path(self, filename: str) -> str:
        return f"uploads/avatars/{filename}"


def test_user_service_enforces_teacher_access_and_updates_avatar() -> None:
    service = UserService(FakeUserRepository(), FakeAvatarStorage())

    with pytest.raises(PermissionDeniedError):
        service.list_users("student")

    profile = service.upload_avatar(UploadAvatarParams(1, "avatar.png", b"png"))
    assert profile.avatar == "/api/user/avatars/avatar.png"
    assert service.get_avatar_path("avatar.png").endswith("avatar.png")

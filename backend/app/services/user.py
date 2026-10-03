"""user 业务参数、结果与服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.clients.avatar_storage_client import AvatarStorageClient
from app.core.errors import PermissionDeniedError, ResourceNotFoundError
from app.persistence.submission import SubmissionRecord
from app.persistence.unit_of_work import UnitOfWork
from app.persistence.user import UserRecord, UserRepository


@dataclass(frozen=True)
class UserProfile:
    """用户公开资料。"""

    id: int
    username: str
    role: str
    avatar: Optional[str]


@dataclass(frozen=True)
class UpdateProfileParams:
    """更新用户资料参数。"""

    avatar: Optional[str] = None


@dataclass(frozen=True)
class UserSubmissionItem:
    """用户提交记录的展示信息。"""

    id: int
    problem_id: int
    problem_title: str
    status: str
    score: float
    language: str
    created_at: datetime
    exam_id: Optional[int]


@dataclass(frozen=True)
class UploadAvatarParams:
    """上传头像所需的业务参数。"""

    user_id: int
    filename: str
    content: bytes


class UserService:
    """编排用户资料、头像和提交记录业务。"""

    def __init__(
        self,
        user_repository: UserRepository,
        avatar_storage_client: AvatarStorageClient,
        *,
        uow: UnitOfWork,
    ) -> None:
        self._uow = uow
        self._user_repository = user_repository
        self._avatar_storage_client = avatar_storage_client

    def list_users(self, requester_role: str) -> list[UserProfile]:
        """供教师查询所有用户。"""
        self._require_teacher(requester_role)
        return [to_user_profile(user) for user in self._user_repository.list_all()]

    def get_profile(self, user_id: int) -> UserProfile:
        """查询用户公开资料。"""
        return to_user_profile(self._require_user(user_id))

    def upload_avatar(self, params: UploadAvatarParams) -> UserProfile:
        """保存头像并更新用户资料。"""
        if not params.filename:
            raise ValueError("未选择头像文件")
        user = self._require_user(params.user_id)
        avatar = self._avatar_storage_client.save(params.filename, params.content)
        updated = to_user_profile(self._user_repository.update_avatar(user, avatar))
        self._uow.commit()
        return updated

    def get_avatar_path(self, filename: str) -> str:
        """获取头像文件的安全路径。"""
        return self._avatar_storage_client.get_path(filename)

    def list_submissions(
        self, requester_id: int, requester_role: str, user_id: int
    ) -> list[UserSubmissionItem]:
        """查询指定用户的提交记录。"""
        if requester_role != "teacher" and requester_id != user_id:
            raise PermissionDeniedError("无权查看该用户的提交记录")
        self._require_user(user_id)
        return [
            to_user_submission_item(item)
            for item in self._user_repository.list_submissions(user_id)
        ]

    def _require_user(self, user_id: int) -> UserRecord:
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError("用户不存在")
        return user

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")


def to_user_profile(user: UserRecord) -> UserProfile:
    """用户 快照 → 公开资料。"""

    return UserProfile(
        id=user.id,
        username=user.username,
        role=user.role,
        avatar=user.avatar,
    )


def to_user_submission_item(submission: SubmissionRecord) -> UserSubmissionItem:
    """提交 快照 → 用户提交项（problem_title 取 submission.problem.title，调用方须预取）。"""

    return UserSubmissionItem(
        id=submission.id,
        problem_id=submission.problem_id,
        problem_title=submission.problem.title if submission.problem else "Unknown",
        status=submission.status,
        score=submission.score,
        language=submission.language,
        created_at=submission.created_at,
        exam_id=submission.exam_id,
    )

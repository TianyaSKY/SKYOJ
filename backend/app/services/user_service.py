"""用户资料与提交查询业务服务。"""

from app.clients.avatar_storage_client import AvatarStorageClient
from app.domain.errors import PermissionDeniedError, ResourceNotFoundError
from app.domain.user import UploadAvatarParams, UserProfile, UserSubmissionItem
from app.repositories.user_repository import UserRepository


class UserService:
    """编排用户资料、头像和提交记录业务。"""

    def __init__(
        self,
        user_repository: UserRepository,
        avatar_storage_client: AvatarStorageClient,
    ) -> None:
        self._user_repository = user_repository
        self._avatar_storage_client = avatar_storage_client

    def list_users(self, requester_role: str) -> list[UserProfile]:
        """供教师查询所有用户。"""
        self._require_teacher(requester_role)
        return [self._to_profile(user) for user in self._user_repository.list_all()]

    def get_profile(self, user_id: int) -> UserProfile:
        """查询用户公开资料。"""
        return self._to_profile(self._require_user(user_id))

    def upload_avatar(self, params: UploadAvatarParams) -> UserProfile:
        """保存头像并更新用户资料。"""
        if not params.filename:
            raise ValueError("未选择头像文件")
        user = self._require_user(params.user_id)
        avatar = self._avatar_storage_client.save(params.filename, params.content)
        return self._to_profile(self._user_repository.update_avatar(user, avatar))

    def get_avatar_path(self, filename: str) -> str:
        """获取头像文件的安全路径。"""
        return self._avatar_storage_client.get_path(filename)

    def list_submissions(self, user_id: int) -> list[UserSubmissionItem]:
        """查询指定用户的提交记录。"""
        self._require_user(user_id)
        return [self._to_submission(item) for item in self._user_repository.list_submissions(user_id)]

    def _require_user(self, user_id: int):
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError("用户不存在")
        return user

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

    @staticmethod
    def _to_profile(user) -> UserProfile:
        return UserProfile(id=user.id, username=user.username, role=user.role, avatar=user.avatar)

    @staticmethod
    def _to_submission(submission) -> UserSubmissionItem:
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

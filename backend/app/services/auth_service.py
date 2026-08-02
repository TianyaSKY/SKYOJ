"""认证领域的业务服务。"""

from collections.abc import Callable

from app.domain.auth import (
    AuthUserInfo,
    LoginParams,
    LoginResult,
    RegisterParams,
    RegisterResult,
)
from app.domain.errors import AuthenticationError, InvalidStateError
from app.repositories.user_repository import UserRepository
from app.utils.auth_tools import encode_auth_token
from app.utils.passwords import check_password, hash_password


class AuthService:
    """处理注册和登录业务。"""

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: Callable[[str], str] = hash_password,
        password_checker: Callable[[str, str], bool] = check_password,
        token_encoder: Callable[[int, str], str | bytes | None] = encode_auth_token,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._password_checker = password_checker
        self._token_encoder = token_encoder

    def register(self, params: RegisterParams) -> RegisterResult:
        """注册新用户。"""
        if self._user_repository.get_by_username(params.username) is not None:
            raise InvalidStateError("用户已存在")

        user = self._user_repository.create(
            username=params.username,
            password_hash=self._password_hasher(params.password),
            role="student",
        )
        return RegisterResult(user_id=user.id, username=user.username)

    def login(self, params: LoginParams) -> LoginResult:
        """校验凭据并签发访问令牌。"""
        user = self._user_repository.get_by_username(params.username)
        if user is None or not self._password_checker(user.password_hash, params.password):
            raise AuthenticationError("用户名或密码错误")

        token = self._token_encoder(user.id, user.role)
        if not token:
            raise AuthenticationError("访问令牌生成失败")
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return LoginResult(
            token=token,
            user=AuthUserInfo(id=user.id, username=user.username, role=user.role),
        )

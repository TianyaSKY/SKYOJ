"""认证相关业务参数与结果。"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RegisterParams:
    """注册业务参数。"""

    username: str
    password: str
    role: str = "student"


@dataclass(frozen=True)
class LoginParams:
    """登录业务参数。"""

    username: str
    password: str


@dataclass(frozen=True)
class AuthUserInfo:
    """认证用户基本信息。"""

    id: int
    username: str
    role: str


@dataclass(frozen=True)
class LoginResult:
    """登录业务结果。"""

    token: str
    user: AuthUserInfo


@dataclass(frozen=True)
class RegisterResult:
    """注册业务结果。"""

    user_id: int
    username: str

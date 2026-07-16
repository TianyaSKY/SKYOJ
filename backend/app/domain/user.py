"""用户相关业务参数与结果。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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
class UserSubmissionSummary:
    """用户提交汇总。"""

    total: int
    accepted: int

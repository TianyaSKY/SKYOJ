"""系统字典与仪表盘相关业务参数与结果。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SysConfigItem:
    """系统配置项。"""

    key: str
    val: str


@dataclass(frozen=True)
class SysConfigResponse:
    """系统配置列表响应。"""

    configs: list[SysConfigItem]
    llm_env_ready: bool


@dataclass(frozen=True)
class UpdateConfigParams:
    """更新系统配置所需参数。"""

    key: str
    val: str


@dataclass(frozen=True)
class DashboardStats:
    """仪表盘统计数据。"""

    submissions_today: int
    total_problems: int
    total_users: int
    active_exams: int
    upcoming_exams: int

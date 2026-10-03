"""系统配置与统计业务契约。"""

from dataclasses import dataclass

from app.domain.json import JsonValue


@dataclass(frozen=True)
class UpdateSystemConfigParams:
    values: dict[str, JsonValue]


@dataclass(frozen=True)
class UpdateSystemConfigResult:
    updated_keys: list[str]
    skipped_keys: list[str]


@dataclass(frozen=True)
class SystemStatistics:
    today_submissions: int
    total_problems: int
    total_users: int
    exams_in_period: int

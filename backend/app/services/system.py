"""system 业务参数、结果与服务。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta

from app.core.errors import PermissionDeniedError, ResourceNotFoundError
from app.core.json import JsonObjectResult, JsonValue
from app.core.time import utcnow
from app.persistence.system import SystemRepository
from app.persistence.unit_of_work import UnitOfWork


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


@dataclass(frozen=True)
class SysConfigItem:
    """系统配置项。"""

    key: str
    val: str


@dataclass(frozen=True)
class UpdateConfigParams:
    """更新系统配置所需参数。"""

    key: str
    val: str


class SystemService:
    """编排系统配置与仪表盘统计。"""

    _blocked_keys = {"llm_api_key", "llm_api_url", "llm_model_name"}

    def __init__(self, repository: SystemRepository, *, uow: UnitOfWork) -> None:
        self._uow = uow
        self._repository = repository

    def get_config(self, *, include_llm_endpoint: bool = False) -> JsonObjectResult:
        config: dict[str, JsonValue] = dict(self._repository.get_config())
        for key, value in {
            "title": "SKYOJ",
            "info": "",
            "warning": "false",
            "practice": "true",
        }.items():
            config.setdefault(key, value)
        config["warning"] = str(config["warning"]).lower() == "true"
        config["practice"] = str(config["practice"]).lower() == "true"
        url, model, key = (
            os.getenv(name, "").strip()
            for name in ("LLM_API_URL", "LLM_MODEL_NAME", "LLM_API_KEY")
        )
        config["llm_env_ready"] = bool(url and model and key)
        if include_llm_endpoint:
            config.update({"llm_api_url": url, "llm_model_name": model})
        return JsonObjectResult(config)

    def update_config(
        self, requester_role: str, params: UpdateSystemConfigParams
    ) -> UpdateSystemConfigResult:
        """更新系统配置，只有教师可以执行。"""
        self._require_teacher(requester_role)
        allowed, skipped = {}, []
        for key, value in params.values.items():
            if key in self._blocked_keys:
                skipped.append(key)
            else:
                allowed[key] = (
                    str(value).lower() if isinstance(value, bool) else str(value)
                )
        self._repository.save_config(allowed)
        self._uow.commit()
        return UpdateSystemConfigResult(list(allowed), skipped)

    def delete_config(self, requester_role: str, key: str) -> None:
        """删除系统配置，只有教师可以执行。"""
        self._require_teacher(requester_role)
        if not self._repository.delete_config(key):
            raise ResourceNotFoundError("配置项不存在")
        self._uow.commit()

    def statistics(self, requester_role: str) -> SystemStatistics:
        """获取系统统计，只有教师可以执行。"""
        self._require_teacher(requester_role)
        now = utcnow()
        record = self._repository.statistics(
            now.replace(hour=0, minute=0, second=0, microsecond=0),
            now - timedelta(days=365),
            now + timedelta(days=180),
        )
        return SystemStatistics(
            record.today_submissions,
            record.total_problems,
            record.total_users,
            record.exams_in_period,
        )

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

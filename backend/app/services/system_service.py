"""系统配置业务服务。"""

import os
from datetime import datetime, timedelta

from app.domain.errors import PermissionDeniedError, ResourceNotFoundError
from app.repositories.system_repository import SystemRepository


class SystemService:
    """编排系统配置与仪表盘统计。"""

    _blocked_keys = {"llm_api_key", "llm_api_url", "llm_model_name"}

    def __init__(self, repository: SystemRepository) -> None:
        self._repository = repository

    def get_config(self) -> dict:
        config = self._repository.get_config()
        for key, value in {"title": "SKYOJ", "info": "", "warning": "false", "practice": "true"}.items():
            config.setdefault(key, value)
        config["warning"] = str(config["warning"]).lower() == "true"
        config["practice"] = str(config["practice"]).lower() == "true"
        url, model, key = (os.getenv(name, "").strip() for name in ("LLM_API_URL", "LLM_MODEL_NAME", "LLM_API_KEY"))
        config.update({"llm_api_url": url, "llm_model_name": model, "llm_env_ready": bool(url and model and key)})
        return config

    def update_config(self, requester_role: str, values: dict) -> tuple[list[str], list[str]]:
        """更新系统配置，只有教师可以执行。"""
        self._require_teacher(requester_role)
        allowed, skipped = {}, []
        for key, value in values.items():
            if key in self._blocked_keys:
                skipped.append(key)
            else:
                allowed[key] = str(value).lower() if isinstance(value, bool) else str(value)
        self._repository.save_config(allowed)
        return list(allowed), skipped

    def delete_config(self, requester_role: str, key: str) -> None:
        """删除系统配置，只有教师可以执行。"""
        self._require_teacher(requester_role)
        if not self._repository.delete_config(key):
            raise ResourceNotFoundError("配置项不存在")

    def statistics(self, requester_role: str) -> dict[str, int]:
        """获取系统统计，只有教师可以执行。"""
        self._require_teacher(requester_role)
        now = datetime.utcnow()
        return self._repository.statistics(now.replace(hour=0, minute=0, second=0, microsecond=0), now - timedelta(days=365), now + timedelta(days=180))

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

"""系统设置 API 请求体模型。"""

from typing import Any

from pydantic import RootModel


class UpdateSysConfigBody(RootModel[dict[str, Any]]):
    """更新系统配置请求体。"""
    pass

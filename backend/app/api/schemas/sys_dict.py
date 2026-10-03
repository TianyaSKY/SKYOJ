"""系统设置请求与响应模型，保留动态配置键。"""

from pydantic import BaseModel, JsonValue, RootModel


class UpdateSysConfigBody(RootModel[dict[str, JsonValue]]):
    pass


class SystemConfigResponse(RootModel[dict[str, JsonValue]]):
    pass


class UpdateSysConfigResponse(BaseModel):
    message: str
    updated_keys: list[str]
    skipped_keys: list[str]


class SystemStatisticsResponse(BaseModel):
    today_submissions: int
    total_problems: int
    total_users: int
    exams_in_period: int

"""认证 API 请求体模型。"""

from pydantic import BaseModel, ConfigDict, Field


class RegisterBody(BaseModel):
    """普通用户注册请求体。"""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=6, max_length=128)


class LoginBody(BaseModel):
    """登录请求体。"""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)

"""认证 API 请求体模型。"""

from pydantic import BaseModel, Field


class RegisterBody(BaseModel):
    """注册请求体。"""

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="student", pattern="^(student|teacher)$")


class LoginBody(BaseModel):
    """登录请求体。"""

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

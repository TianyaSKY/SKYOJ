"""题目 API 请求体模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class CreateProblemBody(BaseModel):
    """创建题目请求体。"""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    language: str = Field(pattern="^(python|java|c|cpp)$")
    type: str = Field(pattern="^(acm|oop|kaggle)$")
    time_limit: int = Field(default=1000, ge=100, le=30000)
    memory_limit: int = Field(default=128, ge=16, le=4096)
    template_code: str = ""


class UpdateProblemBody(BaseModel):
    """更新题目请求体（所有字段可选）。"""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = None
    language: Optional[str] = Field(default=None, pattern="^(python|java|c|cpp)$")
    type: Optional[str] = Field(default=None, pattern="^(acm|oop|kaggle)$")
    time_limit: Optional[int] = Field(default=None, ge=100, le=30000)
    memory_limit: Optional[int] = Field(default=None, ge=16, le=4096)
    template_code: Optional[str] = None

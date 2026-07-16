"""提交 API 请求体模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class SubmitCodeBody(BaseModel):
    """提交代码请求体（JSON 模式）。"""

    problem_id: int = Field(ge=1)
    code: str = Field(min_length=1)
    language: str = Field(min_length=1)
    exam_id: Optional[int] = None

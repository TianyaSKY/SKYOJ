"""查重 API 请求体模型。"""

from pydantic import BaseModel, Field


class BatchCheckBody(BaseModel):
    """批量查重请求体。"""

    submission_ids: list[int] = Field(min_length=1)

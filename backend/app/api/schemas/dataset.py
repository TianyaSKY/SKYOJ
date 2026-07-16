"""数据集 API 请求体模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class CreateDatasetBody(BaseModel):
    """上传数据集请求体。"""
    name: str = Field(min_length=1, max_length=128)
    description: Optional[str] = ""

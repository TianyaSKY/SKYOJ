"""数据集响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: str | None
    uploader: str
    file_size: str
    created_at: datetime | None
    download_url: str
    status: str


class PaginatedDatasetsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    datasets: list[DatasetResponse]


class UploadDatasetResponse(BaseModel):
    message: str
    dataset: DatasetResponse


class CreateDatasetBody(BaseModel):
    """上传数据集请求体。"""

    name: str = Field(min_length=1, max_length=128)
    description: str | None = ""

"""数据集相关业务参数与结果。"""

from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, Optional


@dataclass(frozen=True)
class CreateDatasetParams:
    """创建数据集所需参数。"""

    name: str
    description: str
    file_path: str
    file_size: str
    uploader_id: int
    temp_path: Optional[str] = None
    status: str = "pending"


@dataclass(frozen=True)
class UploadDatasetParams:
    """上传数据集所需的业务参数。"""

    requester_role: str
    uploader_id: int
    filename: str
    content: bytes | BinaryIO
    name: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class DatasetListItem:
    """数据集列表项。"""

    id: int
    name: str
    description: str
    uploader: str
    file_size: str
    created_at: Optional[datetime]
    download_url: str
    status: str = "ready"


@dataclass(frozen=True)
class DatasetDetail:
    """数据集详情。"""

    id: int
    name: str
    description: str
    file_path: str
    file_size: str
    uploader_id: int
    uploader: str
    created_at: Optional[datetime]
    status: str = "ready"


@dataclass(frozen=True)
class DatasetDownload:
    """下载数据集所需的文件信息。"""

    file_path: str
    filename: str


@dataclass(frozen=True)
class PaginatedDatasets:
    """分页数据集列表。"""

    total: int
    page: int
    page_size: int
    datasets: list[DatasetListItem]

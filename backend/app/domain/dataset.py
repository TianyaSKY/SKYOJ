"""数据集相关业务参数与结果。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CreateDatasetParams:
    """创建数据集所需参数。"""

    name: str
    description: str
    file_path: str
    file_size: str
    uploader_id: int


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


@dataclass(frozen=True)
class DatasetDetail:
    """数据集详情。"""

    id: int
    name: str
    description: str
    file_path: str
    file_size: str
    uploader_id: int
    created_at: Optional[datetime]

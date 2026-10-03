"""数据集数据库模型、仓储与业务结果映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session, relationship

from app.persistence.database import Base


@dataclass(frozen=True)
class DatasetRecord:
    """数据集持久化快照，包含文件任务所需状态。"""

    id: int
    name: str
    description: str
    file_path: str
    file_size: str
    uploader_id: int
    uploader: str
    created_at: Optional[datetime]
    status: str = "ready"

    temp_path: Optional[str] = None
    file_hash: Optional[str] = None
    error_message: Optional[str] = None


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    file_path = Column(String(256), nullable=False)
    file_size = Column(String(64))
    status = Column(String(32), nullable=False, default="ready", index=True)
    temp_path = Column(String(500), nullable=True)
    file_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User", back_populates="datasets")


class DatasetRepository:
    """封装数据集表的查询与持久化操作。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, dataset_id: int) -> Optional[DatasetRecord]:
        """按主键查询数据集。"""
        dataset = self._db.get(Dataset, dataset_id)
        return _to_dataset_record(dataset) if dataset is not None else None

    def list_all(
        self, page: int | None = None, page_size: int | None = None
    ) -> tuple[list[DatasetRecord], int | None]:
        """倒序查询数据集，必要时在数据库侧分页。"""
        query = self._db.query(Dataset).order_by(Dataset.id.desc())
        if page is None or page_size is None:
            return [_to_dataset_record(dataset) for dataset in query.all()], None
        total = query.count()
        datasets = query.offset((page - 1) * page_size).limit(page_size).all()
        return [_to_dataset_record(dataset) for dataset in datasets], total

    def create(
        self,
        *,
        name: str,
        description: str,
        file_path: str,
        file_size: str,
        uploader_id: int,
        temp_path: Optional[str] = None,
        status: str = "pending",
    ) -> DatasetRecord:
        """创建并持久化数据集记录。"""
        dataset = Dataset(
            name=name,
            description=description,
            file_path=file_path,
            file_size=file_size,
            temp_path=temp_path,
            status=status,
            uploader_id=uploader_id,
        )
        self._db.add(dataset)
        self._db.flush()
        self._db.refresh(dataset)
        return _to_dataset_record(dataset)

    def delete(self, dataset: DatasetRecord) -> None:
        """删除数据集记录。"""
        row = self._db.get(Dataset, dataset.id)
        if row is None:
            return
        self._db.delete(row)
        self._db.flush()

    def mark_ready(
        self, dataset_id: int, *, file_size: str, file_hash: str
    ) -> Optional[DatasetRecord]:
        """文件落盘后将数据集标记为可用。"""
        dataset = self._db.get(Dataset, dataset_id)
        if dataset is None:
            return None
        dataset.status = "ready"
        dataset.file_size = file_size
        dataset.file_hash = file_hash
        dataset.temp_path = None
        dataset.error_message = None
        self._db.flush()
        self._db.refresh(dataset)
        return _to_dataset_record(dataset)

    def mark_failed(
        self, dataset_id: int, error_message: str
    ) -> Optional[DatasetRecord]:
        """文件处理失败后记录错误。"""
        dataset = self._db.get(Dataset, dataset_id)
        if dataset is None:
            return None
        dataset.status = "failed"
        dataset.error_message = error_message[:2000]
        self._db.flush()
        self._db.refresh(dataset)
        return _to_dataset_record(dataset)


def _to_dataset_record(dataset: Dataset) -> DatasetRecord:
    """ORM → 不依赖 Session 的数据集快照。"""

    return DatasetRecord(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description or "",
        file_path=dataset.file_path,
        file_size=dataset.file_size or "",
        uploader_id=dataset.uploader_id,
        uploader=dataset.uploader.username if dataset.uploader else "Unknown",
        created_at=dataset.created_at,
        status=dataset.status or "ready",
        temp_path=dataset.temp_path,
        file_hash=dataset.file_hash,
        error_message=dataset.error_message,
    )

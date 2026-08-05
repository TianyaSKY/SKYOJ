"""数据集数据访问。"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.dataset import Dataset


class DatasetRepository:
    """封装数据集表的查询与持久化操作。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        """按主键查询数据集。"""
        return self._db.get(Dataset, dataset_id)

    def list_all(
        self, page: int | None = None, page_size: int | None = None
    ) -> tuple[list[Dataset], int | None]:
        """倒序查询数据集，必要时在数据库侧分页。"""
        query = self._db.query(Dataset).order_by(Dataset.id.desc())
        if page is None or page_size is None:
            return query.all(), None
        total = query.count()
        return query.offset((page - 1) * page_size).limit(page_size).all(), total

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
    ) -> Dataset:
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
        self._db.commit()
        self._db.refresh(dataset)
        return dataset

    def delete(self, dataset: Dataset) -> None:
        """删除数据集记录。"""
        self._db.delete(dataset)
        self._db.commit()

    def mark_ready(self, dataset_id: int, *, file_size: str, file_hash: str) -> Optional[Dataset]:
        """文件落盘后将数据集标记为可用。"""
        dataset = self.get_by_id(dataset_id)
        if dataset is None:
            return None
        dataset.status = "ready"
        dataset.file_size = file_size
        dataset.file_hash = file_hash
        dataset.temp_path = None
        dataset.error_message = None
        self._db.commit()
        self._db.refresh(dataset)
        return dataset

    def mark_failed(self, dataset_id: int, error_message: str) -> Optional[Dataset]:
        """文件处理失败后记录错误。"""
        dataset = self.get_by_id(dataset_id)
        if dataset is None:
            return None
        dataset.status = "failed"
        dataset.error_message = error_message[:2000]
        self._db.commit()
        self._db.refresh(dataset)
        return dataset

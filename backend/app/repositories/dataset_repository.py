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

    def list(
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
    ) -> Dataset:
        """创建并持久化数据集记录。"""
        dataset = Dataset(
            name=name,
            description=description,
            file_path=file_path,
            file_size=file_size,
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

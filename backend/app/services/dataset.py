"""数据集业务参数、结果与服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, BinaryIO, Optional

from loguru import logger

from app.clients.dataset_storage_client import DatasetStorageClient
from app.domain.errors import (
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)

if TYPE_CHECKING:
    from app.persistence.dataset import DatasetRepository
    from app.services.async_job_service import AsyncJobService


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

@dataclass(frozen=True)
class DatasetRecord(DatasetDetail):
    """数据集持久化快照，包含文件任务所需状态。"""

    temp_path: Optional[str] = None
    file_hash: Optional[str] = None
    error_message: Optional[str] = None


class DatasetService:
    """编排数据集记录和文件的业务流程。"""

    def __init__(
        self,
        dataset_repository: DatasetRepository,
        storage_client: DatasetStorageClient,
        job_service: AsyncJobService,
    ) -> None:
        self._dataset_repository = dataset_repository
        self._storage_client = storage_client
        self._job_service = job_service

    def list_datasets(
        self, page: int | None = None, page_size: int | None = None
    ) -> list[DatasetListItem] | PaginatedDatasets:
        """查询数据集列表。"""
        items, total = self._dataset_repository.list_all(
            page=page, page_size=page_size
        )
        if page is None or page_size is None:
            return items
        return PaginatedDatasets(
            total=total or 0, page=page, page_size=page_size, datasets=items
        )

    def create_dataset(
        self,
        params: CreateDatasetParams,
        content: bytes | BinaryIO,
    ) -> DatasetDetail:
        """创建数据集记录并提交文件写入任务。"""
        temporary_path = ""
        try:
            temporary_path, byte_size = self._storage_client.stage_upload(
                content,
                params.file_path,
            )
            dataset = self._dataset_repository.create(
                name=params.name,
                description=params.description,
                file_path=params.file_path,
                file_size=self._format_file_size(byte_size),
                uploader_id=params.uploader_id,
                temp_path=temporary_path,
                status="pending",
            )
            self._dataset_repository.unit_of_work.commit()
            self._job_service.enqueue_finalize_dataset(dataset.id)
        except Exception:
            if temporary_path:
                self._storage_client.remove_staged(temporary_path)
            raise
        return dataset

    def upload_dataset(self, params: UploadDatasetParams) -> DatasetDetail:
        """校验上传权限、大小和文件路径后创建数据集。"""
        self._require_teacher(params.requester_role)
        if (
            isinstance(params.content, bytes)
            and len(params.content) > DatasetStorageClient.MAX_FILE_SIZE
        ):
            raise InvalidStateError("数据集文件超过 500MB 限制")
        filename, file_path = self._storage_client.prepare_path(params.filename)
        return self.create_dataset(
            CreateDatasetParams(
                name=params.name or filename,
                description=params.description or "",
                file_path=file_path,
                file_size="",
                uploader_id=params.uploader_id,
            ),
            params.content,
        )

    def get_dataset(self, dataset_id: int) -> DatasetDetail:
        """获取数据集详情。"""
        return self._require_dataset(dataset_id)

    def delete_dataset(self, requester_role: str, dataset_id: int) -> None:
        """删除数据集文件和记录。"""
        self._require_teacher(requester_role)
        dataset = self._require_dataset(dataset_id)
        self._storage_client.delete(dataset.file_path, dataset.id)
        if getattr(dataset, "temp_path", None):
            remove_staged = getattr(self._storage_client, "remove_staged", None)
            if callable(remove_staged):
                remove_staged(dataset.temp_path)
        self._dataset_repository.delete(dataset)
        self._dataset_repository.unit_of_work.commit()

    def dataset_file_exists(self, dataset_id: int) -> DatasetDetail:
        """确认数据集及其文件均存在。"""
        detail = self.get_dataset(dataset_id)
        if detail.status not in {"ready", ""}:
            raise InvalidStateError("数据集文件仍在处理中")
        if not self._storage_client.exists(detail.file_path):
            raise ResourceNotFoundError("数据集文件不存在")
        return detail

    def download_dataset(self, dataset_id: int) -> DatasetDownload:
        """获取可下载的数据集文件信息。"""
        detail = self.dataset_file_exists(dataset_id)
        return DatasetDownload(
            file_path=detail.file_path,
            filename=detail.file_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
        )

    def finalize_dataset(self, dataset_id: int) -> DatasetDetail:
        """校验临时文件、计算哈希并移动数据集文件；失败时标记数据集并抛出。

        在 File Worker 中调用；任务侧状态由 run_job 统一处理。
        """
        dataset = self._dataset_repository.get_by_id(dataset_id)
        if dataset is None:
            raise ValueError(f"数据集不存在: {dataset_id}")
        if dataset.status == "ready" and self._storage_client.exists(dataset.file_path):
            return dataset
        try:
            if not dataset.temp_path:
                raise ValueError(f"数据集缺少临时文件: {dataset_id}")

            byte_size, file_hash = self._storage_client.finalize(
                dataset.temp_path,
                dataset.file_path,
                dataset.id,
            )
            dataset = self._dataset_repository.mark_ready(
                dataset.id,
                file_size=self._format_file_size(byte_size),
                file_hash=file_hash,
            )
            if dataset is None:
                raise ResourceNotFoundError("数据集不存在")
            self._dataset_repository.unit_of_work.commit()
            logger.info(
                "数据集文件落盘完成 dataset_id={} sha256={}", dataset.id, file_hash
            )
            return dataset
        except Exception as exc:
            self._dataset_repository.unit_of_work.rollback()
            self._dataset_repository.mark_failed(dataset_id, str(exc))
            self._dataset_repository.unit_of_work.commit()
            raise

    def _require_dataset(self, dataset_id: int) -> DatasetRecord:
        dataset = self._dataset_repository.get_by_id(dataset_id)
        if dataset is None:
            raise ResourceNotFoundError("数据集不存在")
        return dataset

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        return f"{size_bytes / (1024 * 1024):.2f} MB"

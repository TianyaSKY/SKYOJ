"""数据集领域的业务服务。"""

from typing import BinaryIO

from app.clients.dataset_storage_client import DatasetStorageClient
from app.domain.dataset import (
    CreateDatasetParams,
    DatasetDownload,
    DatasetDetail,
    DatasetListItem,
    PaginatedDatasets,
    UploadDatasetParams,
)
from app.domain.errors import InvalidStateError, PermissionDeniedError, ResourceNotFoundError
from app.repositories.dataset_repository import DatasetRepository
from app.services.async_job_service import AsyncJobService


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
        datasets, total = self._dataset_repository.list(page=page, page_size=page_size)
        items = [self._to_list_item(dataset) for dataset in datasets]
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
            self._job_service.enqueue_finalize_dataset(dataset.id)
        except Exception:
            if temporary_path:
                self._storage_client.remove_staged(temporary_path)
            raise
        return self._to_detail(dataset)

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
        return self._to_detail(self._require_dataset(dataset_id))

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

    def _require_dataset(self, dataset_id: int):
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

    @staticmethod
    def _to_list_item(dataset) -> DatasetListItem:
        return DatasetListItem(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description or "",
            uploader=dataset.uploader.username if dataset.uploader else "Unknown",
            file_size=dataset.file_size or "",
            created_at=dataset.created_at,
            status=getattr(dataset, "status", "ready") or "ready",
            download_url=f"/api/datasets/{dataset.id}/download",
        )

    @staticmethod
    def _to_detail(dataset) -> DatasetDetail:
        return DatasetDetail(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description or "",
            file_path=dataset.file_path,
            file_size=dataset.file_size or "",
            uploader_id=dataset.uploader_id,
            uploader=dataset.uploader.username if dataset.uploader else "Unknown",
            created_at=dataset.created_at,
            status=getattr(dataset, "status", "ready") or "ready",
        )

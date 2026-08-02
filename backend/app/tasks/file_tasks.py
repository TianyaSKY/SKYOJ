"""File Worker 任务：数据集文件校验和落盘。"""

from loguru import logger

from app.clients.dataset_storage_client import DatasetStorageClient
from app.database import SessionLocal
from app.domain.async_job import FINALIZE_DATASET_TASK
from app.messaging.celery_app import celery_app
from app.repositories.async_job_repository import AsyncJobRepository
from app.repositories.dataset_repository import DatasetRepository
from app.services.async_job_service import AsyncJobService


@celery_app.task(name=FINALIZE_DATASET_TASK, ignore_result=True)
def finalize_dataset(job_id: int) -> None:
    """校验临时文件、计算哈希并移动数据集文件。"""
    db = SessionLocal()
    job_service = AsyncJobService.from_session(db)
    started = job_service.start_job(
        job_id,
        lease_seconds=job_service.lease_seconds(FINALIZE_DATASET_TASK),
    )
    if started is None:
        db.close()
        return

    dataset_repository = DatasetRepository(db)
    storage_client = DatasetStorageClient()
    dataset_id: int | None = None
    try:
        job = AsyncJobRepository(db).get_by_id(job_id)
        if job is None:
            raise ValueError(f"异步任务不存在: {job_id}")
        payload = job_service.parse_payload(job.payload)
        dataset_id = int(payload["dataset_id"])
        dataset = dataset_repository.get_by_id(dataset_id)
        if dataset is None:
            raise ValueError(f"数据集不存在: {dataset_id}")
        if dataset.status == "ready" and storage_client.exists(dataset.file_path):
            job_service.complete_job(job_id)
            return
        if not dataset.temp_path:
            raise ValueError(f"数据集缺少临时文件: {dataset_id}")

        byte_size, file_hash = storage_client.finalize(
            dataset.temp_path,
            dataset.file_path,
            dataset.id,
        )
        dataset_repository.mark_ready(
            dataset.id,
            file_size=_format_file_size(byte_size),
            file_hash=file_hash,
        )
        job_service.complete_job(job_id)
        logger.info("数据集文件落盘完成 dataset_id={} sha256={}", dataset.id, file_hash)
    except Exception as exc:
        logger.exception("数据集文件任务执行失败 job_id={} dataset_id={}", job_id, dataset_id)
        if dataset_id is not None:
            dataset_repository.mark_failed(dataset_id, str(exc))
        job_service.fail_job(job_id, str(exc))
    finally:
        db.close()


def _format_file_size(size_bytes: int) -> str:
    """格式化文件大小，保持 API 原有返回格式。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


__all__ = ["finalize_dataset"]

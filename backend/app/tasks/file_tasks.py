"""File Worker 任务：数据集文件校验和落盘。"""

from typing import Any

from sqlalchemy.orm import Session

from app.clients.dataset_storage_client import DatasetStorageClient
from app.messaging.celery_app import celery_app
from app.messaging.task_names import FINALIZE_DATASET_TASK
from app.repositories.async_job_repository import AsyncJobRepository
from app.repositories.dataset_repository import DatasetRepository
from app.services.async_job_service import AsyncJobService
from app.services.dataset_service import DatasetService
from app.tasks.base import run_job


@celery_app.task(name=FINALIZE_DATASET_TASK, ignore_result=True)
def finalize_dataset(job_id: int) -> None:
    """校验临时文件、计算哈希并移动数据集文件。"""
    run_job(
        job_id,
        task_name=FINALIZE_DATASET_TASK,
        handler=_handle_finalize_dataset,
    )


def _handle_finalize_dataset(db: Session, payload: dict[str, Any]):
    """在 File Worker 中执行数据集落盘。"""
    service = DatasetService(
        dataset_repository=DatasetRepository(db),
        storage_client=DatasetStorageClient(),
        job_service=AsyncJobService.from_session(db),
    )
    return service.finalize_dataset(int(payload["dataset_id"]))


__all__ = ["finalize_dataset"]

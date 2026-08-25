"""Debug Worker 任务：ACM 调试运行。"""

from typing import Any

from sqlalchemy.orm import Session

from app.messaging.celery_app import celery_app
from app.messaging.task_names import DEBUG_SUBMISSION_TASK
from app.repositories.debug_run_repository import DebugRunRepository
from app.services.debug_service import DebugService
from app.tasks.base import run_job


@celery_app.task(name=DEBUG_SUBMISSION_TASK, ignore_result=True)
def run_debug(job_id: int) -> None:
    """执行一条 ACM 调试运行任务。"""
    run_job(
        job_id,
        task_name=DEBUG_SUBMISSION_TASK,
        handler=_handle_run_debug,
    )


def _handle_run_debug(db: Session, payload: dict[str, Any]) -> None:
    """调用 DebugService 在 worker 中执行调试运行。"""
    raw_id = payload.get("debug_run_id")
    if raw_id is None:
        raise ValueError("Missing required field: debug_run_id")
    try:
        debug_run_id = int(raw_id)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid debug_run_id: {raw_id!r}") from exc
    DebugService(DebugRunRepository(db), job_service=None).run_debug(debug_run_id)


__all__ = ["run_debug"]

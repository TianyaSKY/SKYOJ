"""任务执行骨架：统一领取、执行、完成/失败状态机。

四个 worker 任务入口（judge/ai/file）共用此骨架；各任务只需提供业务 handler
与失败时的草稿/文件侧标记回调。
"""

from typing import Any, Callable

from loguru import logger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.repositories.async_job_repository import AsyncJobRepository
from app.services.async_job_service import AsyncJobService


def run_job(
    job_id: int,
    *,
    task_name: str,
    handler: Callable[[Session, dict[str, Any]], Any],
    on_failed: Callable[[dict[str, Any], Any], None] | None = None,
    permanent_errors: tuple[type[Exception], ...] = (),
) -> Any | None:
    """执行一个异步任务：领取 → handler → complete/fail。

    重复投递（start_job 返回 None）或永久失败时返回 None。
    """
    db = SessionLocal()
    try:
        service = AsyncJobService.from_session(db)
        if (
            service.start_job(job_id, lease_seconds=service.lease_seconds(task_name))
            is None
        ):
            return None  # 已被其他 worker 领取（重复投递）

        job = AsyncJobRepository(db).get_by_id(job_id)
        if job is None:
            raise ValueError(f"异步任务不存在: {job_id}")
        payload = service.parse_payload(job.payload)

        try:
            result = handler(db, payload)
        except permanent_errors as exc:
            service.fail_job(job_id, str(exc), retry=False)
            if on_failed:
                on_failed(payload, str(exc))
            return None
        except Exception as exc:
            logger.exception("异步任务执行失败 job_id={} task={}", job_id, task_name)
            service.fail_job(job_id, str(exc))
            if on_failed:
                on_failed(payload, str(exc))
            return None

        if getattr(result, "status", None) == "failed":
            if on_failed:
                on_failed(payload, result)
        service.complete_job(job_id)
        return result
    finally:
        db.close()

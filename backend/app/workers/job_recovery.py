"""恢复租约过期的异步任务。"""

import time

from loguru import logger

from app.config import JOB_RECOVERY_INTERVAL_SECONDS
from app.database import SessionLocal
from app.services.async_job_service import AsyncJobService


def recover_once() -> int:
    """恢复一轮过期任务。"""
    db = SessionLocal()
    try:
        service = AsyncJobService.from_session(db)
        return service.recover_expired_jobs(limit=100)
    finally:
        db.close()


def main() -> None:
    """以单进程阻塞循环运行恢复器。"""
    while True:
        try:
            recover_once()
            time.sleep(max(1, JOB_RECOVERY_INTERVAL_SECONDS))
        except KeyboardInterrupt:
            logger.info("收到停止信号，任务恢复器退出")
            break
        except Exception:
            logger.exception("任务恢复器执行异常")
            time.sleep(3)


if __name__ == "__main__":
    main()

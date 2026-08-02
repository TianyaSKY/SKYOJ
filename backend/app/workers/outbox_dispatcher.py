"""将数据库中的待发布任务发送到 RabbitMQ。"""

import time

from loguru import logger

from app.database import SessionLocal
from app.services.async_job_service import AsyncJobService


def dispatch_once() -> int:
    """发布一轮 Outbox 任务。"""
    db = SessionLocal()
    try:
        service = AsyncJobService.from_session(db)
        return service.publish_pending_jobs(limit=20)
    finally:
        db.close()


def main() -> None:
    """以单进程阻塞循环运行发布器。"""
    while True:
        try:
            published = dispatch_once()
            if published == 0:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到停止信号，发布器退出")
            break
        except Exception:
            logger.exception("任务发布器执行异常")
            time.sleep(3)


if __name__ == "__main__":
    main()

"""基于线程的后台任务队列包装。"""

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from loguru import logger


class ThreadTaskQueue:
    """轻量线程池任务队列，供 TaskService 投递后台任务。"""

    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ai-draft-worker",
        )

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """投递任务到后台线程，不阻塞调用方。"""

        def _runner() -> None:
            try:
                func(*args, **kwargs)
            except Exception as exc:
                logger.exception("后台任务执行异常: {}", str(exc))

        self._executor.submit(_runner)


_task_queue: ThreadTaskQueue | None = None
_queue_lock = threading.Lock()


def get_task_queue() -> ThreadTaskQueue:
    """获取进程内单例任务队列。"""
    global _task_queue
    if _task_queue is None:
        with _queue_lock:
            if _task_queue is None:
                _task_queue = ThreadTaskQueue(max_workers=4)
    return _task_queue

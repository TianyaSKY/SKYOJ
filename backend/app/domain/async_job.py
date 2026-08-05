"""异步任务领域常量与业务参数。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

JOB_PENDING = "pending"
JOB_RUNNING = "running"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"

DEFAULT_MAX_ATTEMPTS = 3
# 键为消息任务名字符串，与 app.messaging.task_names 保持一致
LEASE_SECONDS = {
    "skyoj.tasks.judge_submission": 10 * 60,
    "skyoj.tasks.execute_test_data": 20 * 60,
    "skyoj.tasks.generate_problem": 10 * 60,
    "skyoj.tasks.generate_test_script": 10 * 60,
    "skyoj.tasks.finalize_dataset": 30 * 60,
}


@dataclass(frozen=True)
class CreateAsyncJobParams:
    """创建异步任务所需参数。"""

    task_name: str
    queue: str
    payload: dict[str, Any]
    dedupe_key: Optional[str] = None
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    available_at: Optional[datetime] = None


@dataclass(frozen=True)
class AsyncJobResult:
    """对外返回的任务状态快照。"""

    id: int
    task_name: str
    queue: str
    status: str
    attempts: int
    max_attempts: int
    lease_until: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


__all__ = [
    "AsyncJobResult",
    "CreateAsyncJobParams",
    "DEFAULT_MAX_ATTEMPTS",
    "JOB_FAILED",
    "JOB_PENDING",
    "JOB_RUNNING",
    "JOB_SUCCEEDED",
    "LEASE_SECONDS",
]

"""异步任务领域常量与业务参数。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.messaging.queues import AI_QUEUE, FILE_QUEUE, JUDGE_QUEUE
from app.messaging.task_names import (
    EXECUTE_TEST_DATA_TASK,
    FINALIZE_DATASET_TASK,
    GENERATE_PROBLEM_TASK,
    GENERATE_TEST_SCRIPT_TASK,
    JUDGE_SUBMISSION_TASK,
)

JOB_PENDING = "pending"
JOB_RUNNING = "running"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"

OUTBOX_PENDING = "pending"
OUTBOX_PUBLISHED = "published"

DEFAULT_MAX_ATTEMPTS = 3
LEASE_SECONDS = {
    JUDGE_SUBMISSION_TASK: 10 * 60,
    EXECUTE_TEST_DATA_TASK: 20 * 60,
    GENERATE_PROBLEM_TASK: 10 * 60,
    GENERATE_TEST_SCRIPT_TASK: 10 * 60,
    FINALIZE_DATASET_TASK: 30 * 60,
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


@dataclass(frozen=True)
class DispatchResult:
    """一次 Outbox 发布循环的结果。"""

    published: int
    failed: int


__all__ = [
    "AI_QUEUE",
    "AsyncJobResult",
    "CreateAsyncJobParams",
    "DEFAULT_MAX_ATTEMPTS",
    "DispatchResult",
    "EXECUTE_TEST_DATA_TASK",
    "FINALIZE_DATASET_TASK",
    "FILE_QUEUE",
    "GENERATE_PROBLEM_TASK",
    "GENERATE_TEST_SCRIPT_TASK",
    "JOB_FAILED",
    "JOB_PENDING",
    "JOB_RUNNING",
    "JOB_SUCCEEDED",
    "JUDGE_QUEUE",
    "JUDGE_SUBMISSION_TASK",
    "LEASE_SECONDS",
    "OUTBOX_PENDING",
    "OUTBOX_PUBLISHED",
]

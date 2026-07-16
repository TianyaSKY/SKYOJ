"""AI 草稿箱相关业务参数与结果。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


# 任务类型
TASK_PROBLEM_GENERATION = "problem_generation"
TASK_TEST_SCRIPT_GENERATION = "test_script_generation"
TASK_TEST_DATA_EXECUTION = "test_data_execution"

# 任务状态
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"


@dataclass(frozen=True)
class SubmitProblemGenerationParams:
    """提交 AI 出题任务参数。"""

    user_id: int
    background: str
    difficulty: str


@dataclass(frozen=True)
class SubmitTestScriptGenerationParams:
    """提交测例脚本生成任务参数。"""

    user_id: int
    problem_id: int
    direction: str
    count: int
    range_info: str


@dataclass(frozen=True)
class SubmitTestDataExecutionParams:
    """提交测例执行任务参数。"""

    user_id: int
    problem_id: int
    code: str
    problem_type: str
    language: str
    source_draft_id: Optional[int] = None


@dataclass(frozen=True)
class SubmitTaskResult:
    """提交异步任务后的结果。"""

    draft_id: int
    status: str
    task_type: str
    title: str


@dataclass(frozen=True)
class AiDraftSummary:
    """草稿列表项。"""

    id: int
    task_type: str
    status: str
    title: str
    problem_id: Optional[int]
    error_message: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    consumed_at: Optional[datetime]


@dataclass(frozen=True)
class AiDraftDetail:
    """草稿详情。"""

    id: int
    task_type: str
    status: str
    title: str
    problem_id: Optional[int]
    request_payload: dict[str, Any]
    result_payload: dict[str, Any]
    error_message: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    consumed_at: Optional[datetime]


@dataclass(frozen=True)
class AiDraftStats:
    """草稿箱统计。"""

    total: int
    pending: int
    running: int
    success: int
    failed: int
    unconsumed_success: int


@dataclass(frozen=True)
class ApplyProblemDraftResult:
    """应用出题草稿创建正式题目后的结果。"""

    problem_id: int
    draft_id: int
    title: str

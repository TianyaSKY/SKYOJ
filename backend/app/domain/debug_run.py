"""ACM 调试运行相关业务参数与结果。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CreateDebugRunParams:
    """创建调试运行的业务参数。"""

    user_id: int
    problem_id: int
    language: str
    code: str
    exam_id: Optional[int] = None


@dataclass(frozen=True)
class DebugRunResult:
    """创建调试运行后的同步结果。"""

    debug_run_id: int
    status: str
    exam_id: Optional[int] = None


@dataclass(frozen=True)
class DebugRunDetail:
    """调试运行详情。"""

    id: int
    status: str
    language: str
    case_name: Optional[str]
    input: Optional[str]
    expected_output: Optional[str]
    actual_output: Optional[str]
    error_output: Optional[str]
    time_used_ms: Optional[int]
    memory_used_kb: Optional[int]
    created_at: Optional[datetime]
    finished_at: Optional[datetime]
    problem_id: int
    user_id: int
    exam_id: Optional[int]


__all__ = [
    "CreateDebugRunParams",
    "DebugRunResult",
    "DebugRunDetail",
]

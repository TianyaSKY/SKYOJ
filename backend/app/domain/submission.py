"""提交相关业务参数与结果。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SubmitParams:
    """提交代码参数。"""

    user_id: int
    problem_id: int
    code: str
    language: str
    exam_id: Optional[int] = None
    session_exam_id: int = -1
    is_file_upload: bool = False
    filename: Optional[str] = None
    file_content: Optional[bytes] = None


@dataclass(frozen=True)
class SubmissionListItem:
    """提交列表项。"""

    id: int
    user_id: int
    username: str
    problem_id: int
    exam_id: Optional[int]
    status: str
    score: float
    language: str
    created_at: Optional[datetime]


@dataclass(frozen=True)
class SubmissionDetail:
    """提交详情。"""

    id: int
    status: str
    score: float
    log: Optional[str]
    code: Optional[str]
    language: str
    exam_id: Optional[int]
    created_at: Optional[datetime]
    case_results: list["CaseResult"] = field(default_factory=list)


@dataclass(frozen=True)
class PaginatedSubmissions:
    """分页提交列表。"""

    total: int
    pages: int
    current_page: int
    submissions: list[SubmissionListItem]


@dataclass(frozen=True)
class SubmissionQuery:
    """查询提交列表的业务参数。"""

    requester_id: int
    requester_role: str
    problem_id: Optional[int] = None
    user_id: Optional[int] = None
    exam_id: Optional[int] = None
    status: Optional[str] = None
    username: Optional[str] = None
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class SubmitResult:
    """提交代码后的结果。"""

    submission_id: int
    status: str
    exam_id: Optional[int] = None


# 单点判题结果：与 ACM 容器内 SingleCaseResult 字段对齐，但只保留对外需要的部分。
# - case_name: 来自测试数据文件名（如 "1"、"2"）
# - status: passed / wrong_answer / tle / runtime_error / compile_error / system_error
# - time_used_ms: 判题耗时（仅 passed/wrong_answer/tle 时记录；其他场景可空）
# - memory_used_kb: 峰值内存（占位，ACM judge 当前未取真实值，可空）
# - input_data / expected_output / actual_output / error_output:
#   仅当 verbose 模式（单点调试）写入，提交整体跑时不带这四个字段以减小行体积。
CaseStatus = str


@dataclass(frozen=True)
class CaseResult:
    """单测试点结果（聚合写入 Submission.case_results JSON 列）。"""

    case_name: str
    status: CaseStatus
    time_used_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    error_output: Optional[str] = None

"""提交相关业务参数与结果。"""

from dataclasses import dataclass
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
    is_file_upload: bool = False
    filename: Optional[str] = None


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


@dataclass(frozen=True)
class PaginatedSubmissions:
    """分页提交列表。"""

    total: int
    pages: int
    current_page: int
    submissions: list[SubmissionListItem]


@dataclass(frozen=True)
class SubmitResult:
    """提交代码后的结果。"""

    submission_id: int
    status: str
    exam_id: Optional[int] = None

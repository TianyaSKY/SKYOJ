"""剽窃检测相关业务参数与结果。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PlagiarismLogItem:
    """剽窃检测日志列表项。"""

    id: int
    submission_id: int
    target_submission_id: Optional[int]
    similarity_score: float
    created_at: Optional[datetime]
    username: Optional[str]
    problem_id: Optional[int]
    problem_title: Optional[str]


@dataclass(frozen=True)
class PlagiarismLogDetail:
    """剽窃检测日志详情。"""

    id: int
    submission_id: int
    target_submission_id: Optional[int]
    similarity_score: float
    created_at: Optional[datetime]
    username: Optional[str]
    problem_id: Optional[int]
    problem_title: Optional[str]
    code_content: Optional[str]
    target_code: Optional[str]


@dataclass(frozen=True)
class BatchCheckParams:
    """批量剽窃检测请求参数。"""

    submission_ids: list[int]


@dataclass(frozen=True)
class PaginatedPlagiarismLogs:
    """分页剽窃检测日志结果。"""

    total: int
    page: int
    page_size: int
    items: list[PlagiarismLogItem]

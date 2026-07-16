"""题目相关业务参数与结果。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CreateProblemParams:
    """创建题目参数。"""

    title: str
    content: str
    language: str
    problem_type: str
    time_limit: int = 1000
    memory_limit: int = 128
    template_code: str = ""


@dataclass(frozen=True)
class UpdateProblemParams:
    """更新题目参数。"""

    title: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    problem_type: Optional[str] = None
    time_limit: Optional[int] = None
    memory_limit: Optional[int] = None
    template_code: Optional[str] = None


@dataclass(frozen=True)
class ProblemListItem:
    """题目列表项。"""

    id: int
    title: str
    problem_type: str
    language: str
    time_limit: int
    memory_limit: int


@dataclass(frozen=True)
class ProblemDetail:
    """题目详情。"""

    id: int
    title: str
    content: str
    problem_type: str
    language: str
    time_limit: int
    memory_limit: int
    template_code: str
    test_case_path: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class PaginatedProblems:
    """分页题目列表。"""

    total: int
    page: int
    page_size: int
    problems: list[ProblemListItem]

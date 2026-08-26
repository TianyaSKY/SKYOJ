"""错题本业务参数与领域 dataclass。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class WrongBookItem:
    """错题列表项（学生视角）。"""

    id: int
    problem_id: int
    problem_title: str
    submission_id: Optional[int]
    first_wrong_at: Optional[datetime]
    latest_wrong_at: Optional[datetime]
    accepted: bool
    reviewed: bool


@dataclass(frozen=True)
class WrongBookStats:
    """错题本统计。"""

    total: int
    unresolved: int
    reviewed: int
    accepted: int


@dataclass(frozen=True)
class ToggleReviewedResult:
    """标记/取消标记已复习。"""

    id: int
    reviewed: bool

"""考试相关业务参数与结果。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CreateExamParams:
    """创建考试参数。"""

    title: str
    description: str
    start_time: datetime
    end_time: datetime
    password: Optional[str] = None
    is_visible: bool = False
    created_by: int = 0


@dataclass(frozen=True)
class UpdateExamParams:
    """更新考试参数。"""

    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    password: Optional[str] = None
    is_visible: Optional[bool] = None


@dataclass(frozen=True)
class EnterExamParams:
    """进入考试参数。"""

    exam_id: int
    password: Optional[str] = None


@dataclass(frozen=True)
class ExamProblemItem:
    """考试题目信息。"""

    problem_id: int
    display_id: Optional[str]
    score: int
    title: str


@dataclass(frozen=True)
class ExamListItem:
    """考试列表项。"""

    id: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    is_visible: bool
    created_by: int
    problem_count: int
    submission_count: int
    has_password: bool


@dataclass(frozen=True)
class ExamDetail:
    """考试详情。"""

    id: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    is_visible: bool
    created_by: int
    has_password: bool
    problems: list[ExamProblemItem]


@dataclass(frozen=True)
class ExamProblemStatus:
    """考试题目状态（当前学生在考试中的每题状态）。"""

    problem_id: int
    display_id: Optional[str]
    title: str
    max_score: int
    status: str
    current_score: float
    last_submitted_at: Optional[datetime]


@dataclass(frozen=True)
class MonitorSubmissionInfo:
    """监控页单次提交信息。"""

    submission_id: Optional[int]
    status: str
    score: float
    time: Optional[str]


@dataclass(frozen=True)
class MonitorProblemInfo:
    """监控页题目头部信息。"""

    problem_id: int
    display_id: Optional[str]
    max_score: int


@dataclass(frozen=True)
class MonitorEntry:
    """监控页单个用户条目。"""

    user_id: int
    username: str
    total_score: float
    submissions: dict[int, MonitorSubmissionInfo]


@dataclass(frozen=True)
class MonitorResult:
    """监控页结果。"""

    exam_title: str
    problems: list[MonitorProblemInfo]
    users: list[MonitorEntry]


@dataclass(frozen=True)
class RankProblemStats:
    """排行榜中单题统计。"""

    solved: bool
    failed_attempts: int
    time: int


@dataclass(frozen=True)
class RankProblemInfo:
    """排行榜题目头部信息。"""

    problem_id: int
    display_id: Optional[str]


@dataclass(frozen=True)
class RankEntry:
    """排行榜单个用户条目。"""

    user_id: int
    username: str
    solved: int
    penalty: int
    problems: dict[int, RankProblemStats]


@dataclass(frozen=True)
class RankResult:
    """排行榜结果。"""

    exam_title: str
    problems: list[RankProblemInfo]
    rank: list[RankEntry]

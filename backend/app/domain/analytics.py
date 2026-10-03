"""平台统计的固定业务契约。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProblemSubmissionCounts:
    problem_id: int
    title: str
    total: int
    accepted: int


@dataclass(frozen=True)
class ProblemPassRate:
    problem_id: int
    title: str
    pass_rate: float
    total: int


@dataclass(frozen=True)
class ProblemDifficulty:
    problem_id: int
    title: str
    difficulty: float
    total: int


@dataclass(frozen=True)
class DailySubmissionCount:
    date: str
    count: int


@dataclass(frozen=True)
class PlatformAnalytics:
    total_submissions: int
    total_accepted: int
    global_pass_rate: float
    total_problems: int
    problem_pass_rates: list[ProblemPassRate]
    problem_difficulty: list[ProblemDifficulty]
    daily_submissions: list[DailySubmissionCount]

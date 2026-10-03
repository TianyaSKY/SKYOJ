"""学情分析响应模型。"""

from pydantic import BaseModel


class ProblemPassRateResponse(BaseModel):
    problem_id: int
    title: str
    pass_rate: float
    total: int


class ProblemDifficultyResponse(BaseModel):
    problem_id: int
    title: str
    difficulty: float
    total: int


class DailySubmissionCountResponse(BaseModel):
    date: str
    count: int


class PlatformAnalyticsResponse(BaseModel):
    total_submissions: int
    total_accepted: int
    global_pass_rate: float
    total_problems: int
    problem_pass_rates: list[ProblemPassRateResponse]
    problem_difficulty: list[ProblemDifficultyResponse]
    daily_submissions: list[DailySubmissionCountResponse]

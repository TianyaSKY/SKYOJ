"""考试 API 请求体模型。"""

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class CreateExamBody(BaseModel):
    """创建考试请求体。"""

    title: str = Field(min_length=1, max_length=100)
    description: str = ""
    start_time: datetime
    end_time: datetime
    contest_type: str = Field(default="icpc", pattern="^(icpc|ioi)$")
    freeze_minutes: Optional[int] = Field(default=None, ge=0)
    password: Optional[str] = None
    is_visible: bool = False
    problem_ids: list[Annotated[int, Field(ge=1)]] = Field(default_factory=list)


class UpdateExamBody(BaseModel):
    """更新考试请求体（所有字段可选）。"""

    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    contest_type: Optional[str] = Field(default=None, pattern="^(icpc|ioi)$")
    freeze_minutes: Optional[int] = Field(default=None, ge=0)
    password: Optional[str] = None
    is_visible: Optional[bool] = None
    problem_ids: Optional[list[Annotated[int, Field(ge=1)]]] = None


class EnterExamBody(BaseModel):
    """进入考试请求体。"""

    password: Optional[str] = None


class AddProblemToExamBody(BaseModel):
    """向考试添加题目请求体。"""

    problem_id: int = Field(ge=1)
    display_id: Optional[str] = None
    score: int = Field(default=100, ge=1)


from app.services.exam import (
    ExamProblemItem,
    MonitorEntry,
    MonitorProblemInfo,
    RankEntry,
    RankProblemInfo,
)


class ExamResponse(BaseModel):
    id: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    contest_type: str
    freeze_minutes: int | None
    is_visible: bool
    created_by: int


class ExamListResponse(ExamResponse):
    problem_count: int
    submission_count: int


class ExamDetailResponse(ExamResponse):
    has_password: bool
    problems: list[ExamProblemItem]


class ExamTokenResponse(BaseModel):
    message: str
    token: str


class EnterExamResponse(ExamTokenResponse):
    exam_id: int


class MonitorResponse(BaseModel):
    exam_title: str
    problems: list[MonitorProblemInfo]
    users: list[MonitorEntry]


class RankResponse(BaseModel):
    exam_title: str
    problems: list[RankProblemInfo]
    rank: list[RankEntry]


class ExamProblemStatusResponse(BaseModel):
    problem_id: int
    display_id: str | None
    title: str
    max_score: int
    status: str
    current_score: float
    last_submitted_at: datetime | None

"""错题本响应模型。"""

from datetime import datetime

from pydantic import BaseModel


class WrongBookStatsResponse(BaseModel):
    total: int
    unresolved: int
    reviewed: int
    accepted: int


class WrongBookItemResponse(BaseModel):
    id: int
    problem_id: int
    problem_title: str
    submission_id: int | None
    first_wrong_at: datetime | None
    latest_wrong_at: datetime | None
    accepted: bool
    reviewed: bool


class WrongBookListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[WrongBookItemResponse]


class ToggleReviewResponse(BaseModel):
    id: int
    reviewed: bool

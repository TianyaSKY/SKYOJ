"""提交 API 请求体模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class SubmitCodeBody(BaseModel):
    """提交代码请求体（JSON 模式）。"""

    problem_id: int = Field(ge=1)
    code: str = Field(min_length=1)
    language: str = Field(min_length=1)
    exam_id: Optional[int] = None


from datetime import datetime

from app.services.submission import CaseResult


class SubmitCodeResponse(BaseModel):
    message: str
    submission_id: int
    status: str
    exam_id: int | None


class SubmissionListResponse(BaseModel):
    id: int
    user_id: int
    username: str
    problem_id: int
    exam_id: int | None
    status: str
    score: float
    language: str
    created_at: datetime | None


class PaginatedSubmissionsResponse(BaseModel):
    total: int
    pages: int
    current_page: int
    submissions: list[SubmissionListResponse]


class SubmissionDetailResponse(BaseModel):
    id: int
    status: str
    score: float
    log: str | None
    code: str | None
    language: str
    exam_id: int | None
    created_at: datetime | None
    case_results: list[CaseResult]

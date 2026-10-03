"""用户响应模型。"""

from datetime import datetime

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: int
    username: str
    role: str
    avatar: str | None


class UploadAvatarResponse(BaseModel):
    message: str
    avatar: str | None


class UserSubmissionResponse(BaseModel):
    id: int
    problem_id: int
    problem_title: str
    status: str
    score: float
    language: str
    created_at: datetime | None
    exam_id: int | None

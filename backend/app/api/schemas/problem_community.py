"""题解 / 标签 / 评论的 Pydantic 请求与响应 schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateSolutionRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=1, max_length=20000)
    language: Optional[str] = Field(None, max_length=50)


class UpdateSolutionRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=20000)
    language: Optional[str] = Field(None, max_length=50)
    is_official: Optional[bool] = None


class SolutionListItemResponse(BaseModel):
    id: int
    problem_id: int
    author_id: int
    author_username: str
    title: str
    language: Optional[str]
    is_official: bool
    vote_count: int
    comment_count: int
    created_at: Optional[datetime]
    content: str
    liked_by_me: bool
    favorited_by_me: bool


class SolutionDetailResponse(BaseModel):
    id: int
    problem_id: int
    author_id: int
    author_username: str
    title: str
    content: str
    language: Optional[str]
    is_official: bool
    status: str
    vote_count: int
    comment_count: int
    view_count: int
    liked_by_me: bool
    favorited_by_me: bool
    favorite_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SolutionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[SolutionListItemResponse]


class ToggleLikeResponse(BaseModel):
    solution_id: int
    liked: bool
    vote_count: int


class ToggleFavoriteResponse(BaseModel):
    solution_id: int
    favorited: bool


class CommentResponse(BaseModel):
    id: int
    solution_id: int
    user_id: int
    username: str
    content: str
    created_at: Optional[datetime]


class CommentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CommentResponse]


class CreateCommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


# --- 标签 ---


class CreateTagRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)


class TagResponse(BaseModel):
    id: int
    slug: str
    name: str
    category: Optional[str]
    description: Optional[str]


class AttachTagRequest(BaseModel):
    tag_id: int
    approved: bool = False

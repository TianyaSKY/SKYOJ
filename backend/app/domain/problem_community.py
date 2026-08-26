"""题解、标签、点赞、评论的业务参数与领域 dataclass。

按 AGENTS.md：Service 接收明确的 dataclass，不接受 dict / kwargs；
写接口的 Pydantic schema 在 api/schemas/ 下，仅在 API 层短暂存在。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CreateSolutionParams:
    """创建题解参数。"""

    problem_id: int
    author_id: int
    title: str
    content: str
    language: Optional[str] = None


@dataclass(frozen=True)
class UpdateSolutionParams:
    """更新题解参数。"""

    solution_id: int
    requester_id: int
    requester_role: str
    title: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    is_official: Optional[bool] = None  # 仅教师


@dataclass(frozen=True)
class SolutionDetail:
    """题解详情。"""

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
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    liked_by_me: bool = False  # 调用方预取


@dataclass(frozen=True)
class SolutionListItem:
    """题解列表项（不含正文）。"""

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


@dataclass(frozen=True)
class CreateCommentParams:
    """新增题解评论。"""

    solution_id: int
    user_id: int
    content: str


@dataclass(frozen=True)
class CommentDetail:
    """题解评论详情。"""

    id: int
    solution_id: int
    user_id: int
    username: str
    content: str
    created_at: Optional[datetime]


@dataclass(frozen=True)
class ToggleLikeResult:
    """点赞/取消点赞返回。"""

    solution_id: int
    liked: bool
    vote_count: int


# --- 标签 ---


@dataclass(frozen=True)
class CreateTagParams:
    """创建标签。"""

    requester_role: str
    slug: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class TagDetail:
    """标签详情。"""

    id: int
    slug: str
    name: str
    category: Optional[str]
    description: Optional[str]


@dataclass(frozen=True)
class AttachTagParams:
    """给题目贴标签。"""

    problem_id: int
    tag_id: int
    approved: bool
    requester_role: str
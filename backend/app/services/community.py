"""community 业务参数、结果与服务。"""

from __future__ import annotations

from app.core.errors import InvalidStateError, PermissionDeniedError, ResourceNotFoundError
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy.orm import Session
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
    liked_by_me: bool = False
    favorited_by_me: bool = False
    favorite_count: int = 0


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


@dataclass(frozen=True)
class ToggleFavoriteResult:
    """收藏/取消收藏返回。"""

    solution_id: int
    favorited: bool


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


from app.persistence.community import ProblemCommunityRepository, from_comment_orm, from_solution_list_orm, from_solution_orm, from_tag_orm


class SolutionService:
    """题解业务编排：发布、修订、点赞、评论、官方标记、隐藏。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = ProblemCommunityRepository(db)

    # -- 题解 --

    def create(self, params: CreateSolutionParams) -> SolutionDetail:
        solution = self._repo.create_solution(
            problem_id=params.problem_id,
            author_id=params.author_id,
            title=params.title,
            content=params.content,
            language=params.language,
        )
        self._db.commit()
        self._db.refresh(solution)
        return from_solution_orm(solution, viewer_id=params.author_id)

    def update(self, params: UpdateSolutionParams) -> SolutionDetail:
        solution = self._repo.get_solution_by_id(params.solution_id)
        if solution is None:
            raise ResourceNotFoundError("题解不存在")

        if params.requester_id != solution.author_id and params.requester_role != "teacher":
            raise PermissionDeniedError("无权修改该题解")

        if params.is_official is not None:
            if params.requester_role != "teacher":
                raise PermissionDeniedError("仅教师可标记官方题解")
            solution.is_official = params.is_official

        if params.title is not None:
            solution.title = params.title
        if params.content is not None:
            solution.content = params.content
        if params.language is not None:
            solution.language = params.language

        self._db.commit()
        self._db.refresh(solution)
        return from_solution_orm(solution, viewer_id=params.requester_id)

    def hide(self, solution_id: int, requester_id: int, requester_role: str) -> None:
        """作者或教师可隐藏题解（前端不再展示，但不删除）。"""
        solution = self._repo.get_solution_by_id(solution_id)
        if solution is None:
            raise ResourceNotFoundError("题解不存在")
        if requester_id != solution.author_id and requester_role != "teacher":
            raise PermissionDeniedError("无权隐藏该题解")
        solution.status = "hidden"
        self._db.commit()

    def get(self, solution_id: int, viewer_id: int) -> SolutionDetail:
        solution = self._repo.get_solution_by_id(solution_id)
        if solution is None or solution.status == "hidden":
            raise ResourceNotFoundError("题解不存在")
        solution.view_count = (solution.view_count or 0) + 1
        self._db.commit()
        return from_solution_orm(solution, viewer_id=viewer_id)

    def list_for_problem(
        self, problem_id: int, viewer_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[SolutionListItem], int]:
        rows, total = self._repo.list_solutions(
            problem_id=problem_id, only_published=True, page=page, page_size=page_size
        )
        return [from_solution_list_orm(row) for row in rows], total

    # -- 点赞 --

    def toggle_like(self, solution_id: int, user_id: int) -> ToggleLikeResult:
        solution = self._repo.get_solution_by_id(solution_id)
        if solution is None or solution.status == "hidden":
            raise ResourceNotFoundError("题解不存在")
        existing = self._repo.get_like(solution_id, user_id)
        if existing is None:
            self._repo.add_like(solution_id, user_id)
            solution.vote_count = (solution.vote_count or 0) + 1
            self._db.commit()
            return ToggleLikeResult(solution_id=solution_id, liked=True, vote_count=solution.vote_count)
        self._repo.remove_like(existing)
        solution.vote_count = max(0, (solution.vote_count or 0) - 1)
        self._db.commit()
        return ToggleLikeResult(solution_id=solution_id, liked=False, vote_count=solution.vote_count)

    def toggle_favorite(self, solution_id: int, user_id: int) -> ToggleFavoriteResult:
        solution = self._repo.get_solution_by_id(solution_id)
        if solution is None or solution.status == "hidden":
            raise ResourceNotFoundError("题解不存在")
        existing = self._repo.get_favorite(solution_id, user_id)
        if existing is None:
            self._repo.add_favorite(solution_id, user_id)
            solution.favorite_count = (solution.favorite_count or 0) + 1
            self._db.commit()
            return ToggleFavoriteResult(solution_id=solution_id, favorited=True)
        self._repo.remove_favorite(existing)
        solution.favorite_count = max(0, (solution.favorite_count or 0) - 1)
        self._db.commit()
        return ToggleFavoriteResult(solution_id=solution_id, favorited=False)

    # -- 评论 --

    def add_comment(self, params: CreateCommentParams) -> CommentDetail:
        solution = self._repo.get_solution_by_id(params.solution_id)
        if solution is None or solution.status == "hidden":
            raise ResourceNotFoundError("题解不存在")
        comment = self._repo.create_comment(
            solution_id=params.solution_id, user_id=params.user_id, content=params.content
        )
        solution.comment_count = (solution.comment_count or 0) + 1
        self._db.commit()
        self._db.refresh(comment)
        return from_comment_orm(comment)

    def list_comments(self, solution_id: int, page: int = 1, page_size: int = 50) -> tuple[list[CommentDetail], int]:
        if self._repo.get_solution_by_id(solution_id) is None:
            raise ResourceNotFoundError("题解不存在")
        rows, total = self._repo.list_comments(solution_id, page, page_size)
        return [from_comment_orm(row) for row in rows], total

    def delete_comment(self, comment_id: int, requester_id: int, requester_role: str) -> None:
        comment = self._repo.get_comment_by_id(comment_id)
        if comment is None:
            raise ResourceNotFoundError("评论不存在")
        if requester_id != comment.user_id and requester_role != "teacher":
            raise PermissionDeniedError("无权删除该评论")
        solution = self._repo.get_solution_by_id(comment.solution_id)
        if solution is not None:
            solution.comment_count = max(0, (solution.comment_count or 0) - 1)
        self._repo.delete_comment(comment)
        self._db.commit()


class TagService:
    """题目标签业务。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = ProblemCommunityRepository(db)

    def create(self, params: CreateTagParams) -> TagDetail:
        if params.requester_role != "teacher":
            raise PermissionDeniedError("仅教师可创建标签")
        if self._repo.get_tag_by_slug(params.slug) is not None:
            raise InvalidStateError("标签 slug 已存在")
        tag = self._repo.create_tag(
            slug=params.slug,
            name=params.name,
            category=params.category,
            description=params.description,
        )
        self._db.commit()
        self._db.refresh(tag)
        return from_tag_orm(tag)

    def list_all(self) -> list[TagDetail]:
        rows = self._repo.list_tags()
        return [from_tag_orm(row) for row in rows]

    def attach(self, params: AttachTagParams) -> None:
        """题目贴标签：教师直接 approved=true；其他用户建议（approved=false）。"""
        if self._repo.get_problem_exists(params.problem_id) is None:
            raise ResourceNotFoundError("题目不存在")
        if self._repo.get_tag_by_id(params.tag_id) is None:
            raise ResourceNotFoundError("标签不存在")
        if params.requester_role != "teacher" and params.approved:
            raise PermissionDeniedError("仅教师可正式贴标签")
        existing = self._repo.get_tag_map(params.problem_id, params.tag_id)
        if existing is not None:
            existing.approved = params.approved
        else:
            self._repo.create_tag_map(
                problem_id=params.problem_id, tag_id=params.tag_id, approved=params.approved
            )
        self._db.commit()

    def detach(self, problem_id: int, tag_id: int, requester_role: str) -> None:
        if requester_role != "teacher":
            raise PermissionDeniedError("仅教师可移除标签")
        link = self._repo.get_tag_map(problem_id, tag_id)
        if link is not None:
            self._repo.delete_tag_map(link)
            self._db.commit()

    def list_for_problem(self, problem_id: int) -> list[TagDetail]:
        rows = self._repo.list_tags_for_problem(problem_id)
        return [from_tag_orm(row) for row in rows]

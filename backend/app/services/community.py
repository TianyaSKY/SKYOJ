"""community 业务参数、结果与服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.errors import (
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.persistence.community import (
    ProblemCommunityRepository,
    ProblemSolutionCommentRecord,
    ProblemSolutionRecord,
    ProblemTagRecord,
)
from app.persistence.unit_of_work import UnitOfWork


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
    """供题解面板直接展示、编辑的列表项。"""

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


class SolutionService:
    """题解业务编排：发布、修订、点赞、评论、官方标记、隐藏。"""

    def __init__(
        self, repository: ProblemCommunityRepository, *, uow: UnitOfWork
    ) -> None:
        self._uow = uow
        self._repo = repository

    # -- 题解 --

    def create(self, params: CreateSolutionParams) -> SolutionDetail:
        with self._uow.transaction():
            solution = self._repo.create_solution(
                problem_id=params.problem_id,
                author_id=params.author_id,
                title=params.title,
                content=params.content,
                language=params.language,
            )
            if solution is not None:
                solution = self._repo.save_solution(solution)
            return to_solution_detail(solution, viewer_id=params.author_id)

    def update(self, params: UpdateSolutionParams) -> SolutionDetail:
        with self._uow.transaction():
            solution = self._repo.get_solution_by_id(params.solution_id)
            if solution is None:
                raise ResourceNotFoundError("题解不存在")

            if (
                params.requester_id != solution.author_id
                and params.requester_role != "teacher"
            ):
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

            if solution is not None:
                solution = self._repo.save_solution(solution)
            return to_solution_detail(solution, viewer_id=params.requester_id)

    def hide(self, solution_id: int, requester_id: int, requester_role: str) -> None:
        """作者或教师可隐藏题解（前端不再展示，但不删除）。"""
        with self._uow.transaction():
            solution = self._repo.get_solution_by_id(solution_id)
            if solution is None:
                raise ResourceNotFoundError("题解不存在")
            if requester_id != solution.author_id and requester_role != "teacher":
                raise PermissionDeniedError("无权隐藏该题解")
            solution.status = "hidden"
            if solution is not None:
                solution = self._repo.save_solution(solution)

    def get(self, solution_id: int, viewer_id: int) -> SolutionDetail:
        with self._uow.transaction():
            solution = self._repo.get_solution_by_id(solution_id)
            if solution is None or solution.status == "hidden":
                raise ResourceNotFoundError("题解不存在")
            solution.view_count = (solution.view_count or 0) + 1
            if solution is not None:
                solution = self._repo.save_solution(solution)
            return to_solution_detail(solution, viewer_id=viewer_id)

    def list_for_problem(
        self, problem_id: int, viewer_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[SolutionListItem], int]:
        rows, total = self._repo.list_solutions(
            problem_id=problem_id, only_published=True, page=page, page_size=page_size
        )
        return [to_solution_list_item(row, viewer_id=viewer_id) for row in rows], total

    # -- 点赞 --

    def toggle_like(self, solution_id: int, user_id: int) -> ToggleLikeResult:
        with self._uow.transaction():
            solution = self._repo.get_solution_by_id(solution_id)
            if solution is None or solution.status == "hidden":
                raise ResourceNotFoundError("题解不存在")
            existing = self._repo.get_like(solution_id, user_id)
            if existing is None:
                self._repo.add_like(solution_id, user_id)
                solution.vote_count = (solution.vote_count or 0) + 1
                if solution is not None:
                    solution = self._repo.save_solution(solution)
                return ToggleLikeResult(
                    solution_id=solution_id, liked=True, vote_count=solution.vote_count
                )
            self._repo.remove_like(existing)
            solution.vote_count = max(0, (solution.vote_count or 0) - 1)
            if solution is not None:
                solution = self._repo.save_solution(solution)
            return ToggleLikeResult(
                solution_id=solution_id, liked=False, vote_count=solution.vote_count
            )

    def toggle_favorite(self, solution_id: int, user_id: int) -> ToggleFavoriteResult:
        with self._uow.transaction():
            solution = self._repo.get_solution_by_id(solution_id)
            if solution is None or solution.status == "hidden":
                raise ResourceNotFoundError("题解不存在")
            existing = self._repo.get_favorite(solution_id, user_id)
            if existing is None:
                self._repo.add_favorite(solution_id, user_id)
                solution.favorite_count = (solution.favorite_count or 0) + 1
                if solution is not None:
                    solution = self._repo.save_solution(solution)
                return ToggleFavoriteResult(solution_id=solution_id, favorited=True)
            self._repo.remove_favorite(existing)
            solution.favorite_count = max(0, (solution.favorite_count or 0) - 1)
            if solution is not None:
                solution = self._repo.save_solution(solution)
            return ToggleFavoriteResult(solution_id=solution_id, favorited=False)

    # -- 评论 --

    def add_comment(self, params: CreateCommentParams) -> CommentDetail:
        with self._uow.transaction():
            solution = self._repo.get_solution_by_id(params.solution_id)
            if solution is None or solution.status == "hidden":
                raise ResourceNotFoundError("题解不存在")
            comment = self._repo.create_comment(
                solution_id=params.solution_id,
                user_id=params.user_id,
                content=params.content,
            )
            solution.comment_count = (solution.comment_count or 0) + 1
            if solution is not None:
                solution = self._repo.save_solution(solution)
            return to_comment_detail(comment)

    def list_comments(
        self, solution_id: int, page: int = 1, page_size: int = 50
    ) -> tuple[list[CommentDetail], int]:
        solution = self._repo.get_solution_by_id(solution_id)
        if solution is None or solution.status == "hidden":
            raise ResourceNotFoundError("题解不存在")
        rows, total = self._repo.list_comments(solution_id, page, page_size)
        return [to_comment_detail(row) for row in rows], total

    def delete_comment(
        self, comment_id: int, requester_id: int, requester_role: str
    ) -> None:
        with self._uow.transaction():
            comment = self._repo.get_comment_by_id(comment_id)
            if comment is None:
                raise ResourceNotFoundError("评论不存在")
            if requester_id != comment.user_id and requester_role != "teacher":
                raise PermissionDeniedError("无权删除该评论")
            solution = self._repo.get_solution_by_id(comment.solution_id)
            if solution is not None:
                solution.comment_count = max(0, (solution.comment_count or 0) - 1)
            self._repo.delete_comment(comment)
            if solution is not None:
                solution = self._repo.save_solution(solution)


class TagService:
    """题目标签业务。"""

    def __init__(
        self, repository: ProblemCommunityRepository, *, uow: UnitOfWork
    ) -> None:
        self._uow = uow
        self._repo = repository

    def create(self, params: CreateTagParams) -> TagDetail:
        with self._uow.transaction():
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
            return to_tag_detail(tag)

    def list_all(self) -> list[TagDetail]:
        rows = self._repo.list_tags()
        return [to_tag_detail(row) for row in rows]

    def attach(self, params: AttachTagParams) -> None:
        """题目贴标签：教师直接 approved=true；其他用户建议（approved=false）。"""
        with self._uow.transaction():
            if self._repo.get_problem_exists(params.problem_id) is None:
                raise ResourceNotFoundError("题目不存在")
            if self._repo.get_tag_by_id(params.tag_id) is None:
                raise ResourceNotFoundError("标签不存在")
            if params.requester_role != "teacher" and params.approved:
                raise PermissionDeniedError("仅教师可正式贴标签")
            existing = self._repo.get_tag_map(params.problem_id, params.tag_id)
            if existing is not None:
                if params.requester_role != "teacher" and existing.approved:
                    raise PermissionDeniedError("仅教师可更改已批准的标签")
                existing.approved = params.approved
                self._repo.save_tag_map(existing)
            else:
                self._repo.create_tag_map(
                    problem_id=params.problem_id,
                    tag_id=params.tag_id,
                    approved=params.approved,
                )

    def detach(self, problem_id: int, tag_id: int, requester_role: str) -> None:
        with self._uow.transaction():
            if requester_role != "teacher":
                raise PermissionDeniedError("仅教师可移除标签")
            link = self._repo.get_tag_map(problem_id, tag_id)
            if link is not None:
                self._repo.delete_tag_map(link)

    def list_for_problem(self, problem_id: int) -> list[TagDetail]:
        rows = self._repo.list_tags_for_problem(problem_id)
        return [to_tag_detail(row) for row in rows]


def to_solution_detail(
    solution: ProblemSolutionRecord, *, viewer_id: int | None = None
) -> SolutionDetail:
    """题解 快照 → 详情；liked_by_me / favorited_by_me 视调用方预取的 viewer_id 是否点赞/收藏决定。"""

    liked_by_me = False
    favorited_by_me = False
    if viewer_id is not None and solution.likes is not None:
        liked_by_me = any(like.user_id == viewer_id for like in solution.likes)
    if viewer_id is not None and solution.favorites is not None:
        favorited_by_me = any(fav.user_id == viewer_id for fav in solution.favorites)
    return SolutionDetail(
        id=solution.id,
        problem_id=solution.problem_id,
        author_id=solution.author_id,
        author_username=solution.author.username if solution.author else "Unknown",
        title=solution.title,
        content=solution.content,
        language=solution.language,
        is_official=bool(solution.is_official),
        status=solution.status,
        vote_count=solution.vote_count or 0,
        comment_count=solution.comment_count or 0,
        view_count=solution.view_count or 0,
        created_at=solution.created_at,
        updated_at=solution.updated_at,
        liked_by_me=liked_by_me,
        favorited_by_me=favorited_by_me,
        favorite_count=solution.favorite_count or 0,
    )


def to_solution_list_item(
    solution: ProblemSolutionRecord, *, viewer_id: int
) -> SolutionListItem:
    """题解快照转为列表项，复用已预取的点赞和收藏关系。"""

    return SolutionListItem(
        id=solution.id,
        problem_id=solution.problem_id,
        author_id=solution.author_id,
        author_username=solution.author.username if solution.author else "Unknown",
        title=solution.title,
        language=solution.language,
        is_official=bool(solution.is_official),
        vote_count=solution.vote_count or 0,
        comment_count=solution.comment_count or 0,
        created_at=solution.created_at,
        content=solution.content,
        liked_by_me=any(like.user_id == viewer_id for like in solution.likes or []),
        favorited_by_me=any(fav.user_id == viewer_id for fav in solution.favorites or []),
    )


def to_comment_detail(comment: ProblemSolutionCommentRecord) -> CommentDetail:

    return CommentDetail(
        id=comment.id,
        solution_id=comment.solution_id,
        user_id=comment.user_id,
        username=comment.user.username if comment.user else "Unknown",
        content=comment.content,
        created_at=comment.created_at,
    )


def to_tag_detail(tag: ProblemTagRecord) -> TagDetail:

    return TagDetail(
        id=tag.id,
        slug=tag.slug,
        name=tag.name,
        category=tag.category,
        description=tag.description,
    )

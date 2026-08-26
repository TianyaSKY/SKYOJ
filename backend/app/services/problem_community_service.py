"""题解、标签、点赞、评论的服务编排。

按 AGENTS.md：业务规则、流程编排、事务、重试与补偿都集中于此；
仓储负责数据访问，本模块不直接接触 SQLAlchemy API。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.errors import (
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.domain.problem_community import (
    AttachTagParams,
    CommentDetail,
    CreateCommentParams,
    CreateSolutionParams,
    CreateTagParams,
    SolutionDetail,
    SolutionListItem,
    TagDetail,
    ToggleLikeResult,
    UpdateSolutionParams,
)
from app.mappers import from_solution_orm, from_solution_list_orm, from_comment_orm, from_tag_orm
from app.repositories.problem_community_repository import ProblemCommunityRepository


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
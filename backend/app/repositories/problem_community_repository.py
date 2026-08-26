"""题解 / 标签 / 点赞 / 评论的仓储层。

不做业务规则校验（service 层职责），只做 SQL 映射；
所有写方法立即生效（flush），由调用方 commit。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.problem import Problem
from app.models.problem_community import (
    ProblemSolution,
    ProblemSolutionComment,
    ProblemSolutionLike,
    ProblemTag,
    ProblemTagMap,
)
from app.models.user import User


class ProblemCommunityRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # -- 题解 --

    def create_solution(
        self,
        *,
        problem_id: int,
        author_id: int,
        title: str,
        content: str,
        language: Optional[str],
    ) -> ProblemSolution:
        solution = ProblemSolution(
            problem_id=problem_id,
            author_id=author_id,
            title=title,
            content=content,
            language=language,
            status="published",
        )
        self._db.add(solution)
        self._db.flush()
        return solution

    def get_solution_by_id(self, solution_id: int) -> Optional[ProblemSolution]:
        return (
            self._db.query(ProblemSolution)
            .options(selectinload(ProblemSolution.author))
            .filter(ProblemSolution.id == solution_id)
            .first()
        )

    def list_solutions(
        self,
        *,
        problem_id: int,
        only_published: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProblemSolution], int]:
        query = self._db.query(ProblemSolution).options(
            selectinload(ProblemSolution.author)
        )
        query = query.filter(ProblemSolution.problem_id == problem_id)
        if only_published:
            query = query.filter(ProblemSolution.status == "published")
        total = query.count()
        rows = (
            query.order_by(
                ProblemSolution.is_official.desc(),
                ProblemSolution.vote_count.desc(),
                ProblemSolution.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    # -- 点赞 --

    def get_like(self, solution_id: int, user_id: int) -> Optional[ProblemSolutionLike]:
        return (
            self._db.query(ProblemSolutionLike)
            .filter(
                ProblemSolutionLike.solution_id == solution_id,
                ProblemSolutionLike.user_id == user_id,
            )
            .first()
        )

    def add_like(self, solution_id: int, user_id: int) -> ProblemSolutionLike:
        like = ProblemSolutionLike(solution_id=solution_id, user_id=user_id)
        self._db.add(like)
        self._db.flush()
        return like

    def remove_like(self, like: ProblemSolutionLike) -> None:
        self._db.delete(like)
        self._db.flush()

    def list_likers(self, solution_id: int) -> list[int]:
        rows = (
            self._db.query(ProblemSolutionLike.user_id)
            .filter(ProblemSolutionLike.solution_id == solution_id)
            .all()
        )
        return [row[0] for row in rows]

    # -- 评论 --

    def create_comment(
        self, *, solution_id: int, user_id: int, content: str
    ) -> ProblemSolutionComment:
        comment = ProblemSolutionComment(
            solution_id=solution_id, user_id=user_id, content=content
        )
        self._db.add(comment)
        self._db.flush()
        return comment

    def get_comment_by_id(self, comment_id: int) -> Optional[ProblemSolutionComment]:
        return self._db.get(ProblemSolutionComment, comment_id)

    def list_comments(
        self, solution_id: int, page: int = 1, page_size: int = 50
    ) -> tuple[list[ProblemSolutionComment], int]:
        query = self._db.query(ProblemSolutionComment).options(
            selectinload(ProblemSolutionComment.user)
        ).filter(ProblemSolutionComment.solution_id == solution_id)
        total = query.count()
        rows = (
            query.order_by(ProblemSolutionComment.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def delete_comment(self, comment: ProblemSolutionComment) -> None:
        self._db.delete(comment)
        self._db.flush()

    # -- 标签 --

    def get_tag_by_id(self, tag_id: int) -> Optional[ProblemTag]:
        return self._db.get(ProblemTag, tag_id)

    def get_tag_by_slug(self, slug: str) -> Optional[ProblemTag]:
        return self._db.query(ProblemTag).filter(ProblemTag.slug == slug).first()

    def list_tags(self) -> list[ProblemTag]:
        return (
            self._db.query(ProblemTag)
            .order_by(ProblemTag.category, ProblemTag.name)
            .all()
        )

    def create_tag(
        self,
        *,
        slug: str,
        name: str,
        category: Optional[str],
        description: Optional[str],
    ) -> ProblemTag:
        tag = ProblemTag(
            slug=slug, name=name, category=category, description=description
        )
        self._db.add(tag)
        self._db.flush()
        return tag

    def get_problem_exists(self, problem_id: int) -> Optional[Problem]:
        return self._db.get(Problem, problem_id)

    def get_tag_map(self, problem_id: int, tag_id: int) -> Optional[ProblemTagMap]:
        return (
            self._db.query(ProblemTagMap)
            .filter(
                ProblemTagMap.problem_id == problem_id,
                ProblemTagMap.tag_id == tag_id,
            )
            .first()
        )

    def create_tag_map(
        self, *, problem_id: int, tag_id: int, approved: bool
    ) -> ProblemTagMap:
        link = ProblemTagMap(problem_id=problem_id, tag_id=tag_id, approved=approved)
        self._db.add(link)
        self._db.flush()
        return link

    def delete_tag_map(self, link: ProblemTagMap) -> None:
        self._db.delete(link)
        self._db.flush()

    def list_tags_for_problem(self, problem_id: int) -> list[ProblemTag]:
        rows = (
            self._db.query(ProblemTag)
            .join(ProblemTagMap, ProblemTagMap.tag_id == ProblemTag.id)
            .filter(ProblemTagMap.problem_id == problem_id)
            .order_by(ProblemTag.name)
            .all()
        )
        return rows
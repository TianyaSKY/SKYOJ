"""community 数据库模型、仓储与映射。"""

from __future__ import annotations

from app.persistence.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Session, relationship, selectinload
from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from app.persistence.problem import Problem
    from app.services.community import CommentDetail, SolutionDetail, SolutionListItem, TagDetail


class ProblemTag(Base):
    """知识点/分类标签（如：贪心 / DP / 图论 / 二分 / 链表）。"""

    __tablename__ = "problem_tags"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_problem_tags_slug"),
        Index("ix_problem_tags_category", "category"),
    )

    id = Column(Integer, primary_key=True)
    slug = Column(String(50), nullable=False)  # url-friendly 短标识
    name = Column(String(100), nullable=False)  # 展示名
    category = Column(String(50), nullable=True)  # 主题分类（可选）
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ProblemTag {self.slug}>"


class ProblemTagMap(Base):
    """题目 ↔ 标签 多对多关联。"""

    __tablename__ = "problem_tag_maps"
    __table_args__ = (
        UniqueConstraint("problem_id", "tag_id", name="uq_problem_tag_maps_pair"),
        Index("ix_problem_tag_maps_problem", "problem_id"),
        Index("ix_problem_tag_maps_tag", "tag_id"),
    )

    id = Column(Integer, primary_key=True)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    tag_id = Column(
        Integer, ForeignKey("problem_tags.id", ondelete="CASCADE"), nullable=False
    )
    # 由教师/题解作者标记；普通用户建议的标签留 NULL 由教师复审。
    approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ProblemTagMap problem={self.problem_id} tag={self.tag_id}>"


class ProblemSolution(Base):
    """题目题解主体。每名用户对同一题目可发布多个版本（保留修订）。

    字段：
    - is_official: 教师标记为官方题解，列表优先置顶。
    - status: published / hidden / pending；普通用户首发即 published。
    - vote_count / comment_count: 冗余计数字段，写入时即时维护，避免读路径
      COUNT(*)。单表行数 < 10 万时维护代价低。
    """

    __tablename__ = "problem_solutions"
    __table_args__ = (
        Index("ix_problem_solutions_problem", "problem_id"),
        Index("ix_problem_solutions_author", "author_id"),
        Index(
            "ix_problem_solutions_problem_status",
            "problem_id",
            "status",
            "is_official",
            "vote_count",
        ),
    )

    id = Column(Integer, primary_key=True)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # Markdown
    language = Column(String(50), nullable=True)  # 代码示例语言（可选）

    is_official = Column(Boolean, default=False, nullable=False)
    status = Column(
        Enum(
            "published",
            "hidden",
            "pending",
            name="problem_solutions_status",
        ),
        default="published",
        nullable=False,
    )

    vote_count = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    view_count = Column(Integer, default=0, nullable=False)
    favorite_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # ORM 关系
    problem = relationship("Problem", back_populates="solutions")
    author = relationship("User")
    likes = relationship(
        "ProblemSolutionLike",
        back_populates="solution",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "ProblemSolutionComment",
        back_populates="solution",
        cascade="all, delete-orphan",
    )
    favorites = relationship(
        "ProblemSolutionFavorite",
        back_populates="solution",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ProblemSolution {self.id} problem={self.problem_id}>"


class ProblemSolutionLike(Base):
    """题解点赞关系表。每用户每题解一条记录。"""

    __tablename__ = "problem_solution_likes"
    __table_args__ = (
        UniqueConstraint(
            "solution_id", "user_id", name="uq_problem_solution_likes_pair"
        ),
        Index("ix_problem_solution_likes_user", "user_id"),
    )

    id = Column(Integer, primary_key=True)
    solution_id = Column(
        Integer,
        ForeignKey("problem_solutions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    solution = relationship("ProblemSolution", back_populates="likes")

    def __repr__(self) -> str:
        return f"<ProblemSolutionLike solution={self.solution_id} user={self.user_id}>"


class ProblemSolutionFavorite(Base):
    """题解收藏关系表。每用户每题解一条记录（与点赞不同，收藏不计入 vote_count）。"""

    __tablename__ = "problem_solution_favorites"
    __table_args__ = (
        UniqueConstraint(
            "solution_id", "user_id", name="uq_problem_solution_favorites_pair"
        ),
        Index("ix_problem_solution_favorites_user", "user_id"),
    )

    id = Column(Integer, primary_key=True)
    solution_id = Column(
        Integer,
        ForeignKey("problem_solutions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    solution = relationship("ProblemSolution", back_populates="favorites")

    def __repr__(self) -> str:
        return f"<ProblemSolutionFavorite solution={self.solution_id} user={self.user_id}>"


class ProblemSolutionComment(Base):
    """题解评论。扁平（不支持嵌套），按时间正序。"""

    __tablename__ = "problem_solution_comments"
    __table_args__ = (
        Index("ix_problem_solution_comments_solution", "solution_id"),
    )

    id = Column(Integer, primary_key=True)
    solution_id = Column(
        Integer,
        ForeignKey("problem_solutions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    solution = relationship("ProblemSolution", back_populates="comments")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<ProblemSolutionComment {self.id}>"


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

    # -- 收藏 --

    def get_favorite(self, solution_id: int, user_id: int) -> Optional[ProblemSolutionFavorite]:
        return (
            self._db.query(ProblemSolutionFavorite)
            .filter(
                ProblemSolutionFavorite.solution_id == solution_id,
                ProblemSolutionFavorite.user_id == user_id,
            )
            .first()
        )

    def add_favorite(self, solution_id: int, user_id: int) -> ProblemSolutionFavorite:
        fav = ProblemSolutionFavorite(solution_id=solution_id, user_id=user_id)
        self._db.add(fav)
        self._db.flush()
        return fav

    def remove_favorite(self, fav: ProblemSolutionFavorite) -> None:
        self._db.delete(fav)
        self._db.flush()

    def list_favorites_for_user(self, user_id: int) -> list[ProblemSolutionFavorite]:
        return (
            self._db.query(ProblemSolutionFavorite)
            .filter(ProblemSolutionFavorite.user_id == user_id)
            .all()
        )

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

        from app.persistence.problem import Problem
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

    def list_problem_ids_by_tag(self, tag_id: int) -> list[int]:
        rows = (
            self._db.query(ProblemTagMap.problem_id)
            .filter(
                ProblemTagMap.tag_id == tag_id,
                ProblemTagMap.approved == True,  # noqa: E712
            )
            .all()
        )
        return [r[0] for r in rows]


def from_solution_orm(solution, *, viewer_id: int | None = None) -> SolutionDetail:
    """题解 ORM → 详情；liked_by_me / favorited_by_me 视调用方预取的 viewer_id 是否点赞/收藏决定。"""

    from app.services.community import SolutionDetail
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


def from_solution_list_orm(solution) -> SolutionListItem:
    """题解 ORM → 列表项（不含正文）。"""

    from app.services.community import SolutionListItem
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
    )


def from_comment_orm(comment) -> CommentDetail:

    from app.services.community import CommentDetail
    return CommentDetail(
        id=comment.id,
        solution_id=comment.solution_id,
        user_id=comment.user_id,
        username=comment.user.username if comment.user else "Unknown",
        content=comment.content,
        created_at=comment.created_at,
    )


def from_tag_orm(tag) -> TagDetail:

    from app.services.community import TagDetail
    return TagDetail(
        id=tag.id,
        slug=tag.slug,
        name=tag.name,
        category=tag.category,
        description=tag.description,
    )

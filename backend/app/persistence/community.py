"""community 数据库模型、仓储与映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Session, relationship, selectinload

from app.persistence.database import Base
from app.persistence.user import UserRecord


@dataclass
class ProblemSolutionRecord:
    """ProblemSolution 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    problem_id: int
    author_id: int
    title: str
    content: str
    language: str | None
    is_official: bool
    status: str
    vote_count: int
    comment_count: int
    view_count: int
    favorite_count: int
    created_at: datetime | None
    updated_at: datetime
    author: UserRecord | None
    likes: list[ProblemSolutionLikeRecord]
    favorites: list[ProblemSolutionFavoriteRecord]


@dataclass
class ProblemSolutionCommentRecord:
    """ProblemSolutionComment 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    solution_id: int
    user_id: int
    content: str
    created_at: datetime
    user: UserRecord | None


@dataclass
class ProblemSolutionLikeRecord:
    """ProblemSolutionLike 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    solution_id: int
    user_id: int
    created_at: datetime | None


@dataclass
class ProblemSolutionFavoriteRecord:
    """ProblemSolutionFavorite 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    solution_id: int
    user_id: int
    created_at: datetime | None


@dataclass
class ProblemTagRecord:
    """ProblemTag 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    slug: str
    name: str
    category: str | None
    description: str | None
    created_at: datetime | None


@dataclass
class ProblemTagMapRecord:
    """ProblemTagMap 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    problem_id: int
    tag_id: int
    approved: bool
    created_at: datetime | None


if TYPE_CHECKING:
    from app.persistence.problem import ProblemRecord


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
        return (
            f"<ProblemSolutionFavorite solution={self.solution_id} user={self.user_id}>"
        )


class ProblemSolutionComment(Base):
    """题解评论。扁平（不支持嵌套），按时间正序。"""

    __tablename__ = "problem_solution_comments"
    __table_args__ = (Index("ix_problem_solution_comments_solution", "solution_id"),)

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

    def save_solution(self, record: ProblemSolutionRecord) -> ProblemSolutionRecord:
        """将业务修改写回题解行，事务由服务控制。"""
        row = self._db.get(ProblemSolution, record.id)
        for attribute in (
            "title",
            "content",
            "language",
            "is_official",
            "status",
            "vote_count",
            "favorite_count",
            "comment_count",
            "view_count",
        ):
            setattr(row, attribute, getattr(record, attribute))
        self._db.flush()
        self._db.refresh(row)
        return _to_problem_solution_record(row)

    def save_tag_map(self, record: ProblemTagMapRecord) -> None:
        """更新标签审批状态。"""
        row = self._db.get(ProblemTagMap, record.id)
        row.approved = record.approved
        self._db.flush()

    # -- 题解 --

    def create_solution(
        self,
        *,
        problem_id: int,
        author_id: int,
        title: str,
        content: str,
        language: Optional[str],
    ) -> ProblemSolutionRecord:
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
        return _to_problem_solution_record(solution)

    def get_solution_by_id(self, solution_id: int) -> Optional[ProblemSolutionRecord]:
        return _to_problem_solution_record(
            self._db.query(ProblemSolution)
            .options(
                selectinload(ProblemSolution.author),
                selectinload(ProblemSolution.likes),
                selectinload(ProblemSolution.favorites),
            )
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
    ) -> tuple[list[ProblemSolutionRecord], int]:
        query = self._db.query(ProblemSolution).options(
            selectinload(ProblemSolution.author),
            selectinload(ProblemSolution.likes),
            selectinload(ProblemSolution.favorites),
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
        return ([_to_problem_solution_record(row) for row in (rows)], total)

    # -- 点赞 --

    def get_like(
        self, solution_id: int, user_id: int
    ) -> Optional[ProblemSolutionLikeRecord]:
        return _to_problem_solution_like_record(
            self._db.query(ProblemSolutionLike)
            .filter(
                ProblemSolutionLike.solution_id == solution_id,
                ProblemSolutionLike.user_id == user_id,
            )
            .first()
        )

    def add_like(self, solution_id: int, user_id: int) -> ProblemSolutionLikeRecord:
        like = ProblemSolutionLike(solution_id=solution_id, user_id=user_id)
        self._db.add(like)
        self._db.flush()
        return _to_problem_solution_like_record(like)

    def remove_like(self, like: ProblemSolutionLikeRecord) -> None:
        self._db.delete(self._db.get(ProblemSolutionLike, like.id))
        self._db.flush()

    def list_likers(self, solution_id: int) -> list[int]:
        rows = (
            self._db.query(ProblemSolutionLike.user_id)
            .filter(ProblemSolutionLike.solution_id == solution_id)
            .all()
        )
        return [row[0] for row in rows]

    # -- 收藏 --

    def get_favorite(
        self, solution_id: int, user_id: int
    ) -> Optional[ProblemSolutionFavoriteRecord]:
        return _to_problem_solution_favorite_record(
            self._db.query(ProblemSolutionFavorite)
            .filter(
                ProblemSolutionFavorite.solution_id == solution_id,
                ProblemSolutionFavorite.user_id == user_id,
            )
            .first()
        )

    def add_favorite(
        self, solution_id: int, user_id: int
    ) -> ProblemSolutionFavoriteRecord:
        fav = ProblemSolutionFavorite(solution_id=solution_id, user_id=user_id)
        self._db.add(fav)
        self._db.flush()
        return _to_problem_solution_favorite_record(fav)

    def remove_favorite(self, fav: ProblemSolutionFavoriteRecord) -> None:
        self._db.delete(self._db.get(ProblemSolutionFavorite, fav.id))
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
    ) -> ProblemSolutionCommentRecord:
        comment = ProblemSolutionComment(
            solution_id=solution_id, user_id=user_id, content=content
        )
        self._db.add(comment)
        self._db.flush()
        return _to_problem_solution_comment_record(comment)

    def get_comment_by_id(
        self, comment_id: int
    ) -> Optional[ProblemSolutionCommentRecord]:
        return _to_problem_solution_comment_record(
            self._db.get(ProblemSolutionComment, comment_id)
        )

    def list_comments(
        self, solution_id: int, page: int = 1, page_size: int = 50
    ) -> tuple[list[ProblemSolutionCommentRecord], int]:
        query = (
            self._db.query(ProblemSolutionComment)
            .options(selectinload(ProblemSolutionComment.user))
            .filter(ProblemSolutionComment.solution_id == solution_id)
        )
        total = query.count()
        rows = (
            query.order_by(ProblemSolutionComment.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return ([_to_problem_solution_comment_record(row) for row in (rows)], total)

    def delete_comment(self, comment: ProblemSolutionCommentRecord) -> None:
        self._db.delete(self._db.get(ProblemSolutionComment, comment.id))
        self._db.flush()

    # -- 标签 --

    def get_tag_by_id(self, tag_id: int) -> Optional[ProblemTagRecord]:
        return _to_problem_tag_record(self._db.get(ProblemTag, tag_id))

    def get_tag_by_slug(self, slug: str) -> Optional[ProblemTagRecord]:
        return _to_problem_tag_record(
            self._db.query(ProblemTag).filter(ProblemTag.slug == slug).first()
        )

    def list_tags(self) -> list[ProblemTagRecord]:
        return [
            _to_problem_tag_record(row)
            for row in (
                self._db.query(ProblemTag)
                .order_by(ProblemTag.category, ProblemTag.name)
                .all()
            )
        ]

    def create_tag(
        self,
        *,
        slug: str,
        name: str,
        category: Optional[str],
        description: Optional[str],
    ) -> ProblemTagRecord:
        tag = ProblemTag(
            slug=slug, name=name, category=category, description=description
        )
        self._db.add(tag)
        self._db.flush()
        return _to_problem_tag_record(tag)

    def get_problem_exists(self, problem_id: int) -> Optional[ProblemRecord]:

        from app.persistence.problem import Problem, _to_problem_record

        return _to_problem_record(self._db.get(Problem, problem_id))

    def get_tag_map(
        self, problem_id: int, tag_id: int
    ) -> Optional[ProblemTagMapRecord]:
        return _to_problem_tag_map_record(
            self._db.query(ProblemTagMap)
            .filter(
                ProblemTagMap.problem_id == problem_id, ProblemTagMap.tag_id == tag_id
            )
            .first()
        )

    def create_tag_map(
        self, *, problem_id: int, tag_id: int, approved: bool
    ) -> ProblemTagMapRecord:
        link = ProblemTagMap(problem_id=problem_id, tag_id=tag_id, approved=approved)
        self._db.add(link)
        self._db.flush()
        return _to_problem_tag_map_record(link)

    def delete_tag_map(self, link: ProblemTagMapRecord) -> None:
        self._db.delete(self._db.get(ProblemTagMap, link.id))
        self._db.flush()

    def list_tags_for_problem(self, problem_id: int) -> list[ProblemTagRecord]:
        rows = (
            self._db.query(ProblemTag)
            .join(ProblemTagMap, ProblemTagMap.tag_id == ProblemTag.id)
            .filter(ProblemTagMap.problem_id == problem_id)
            .order_by(ProblemTag.name)
            .all()
        )
        return [_to_problem_tag_record(row) for row in (rows)]

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


def _to_problem_solution_record(
    row: ProblemSolution | None,
) -> ProblemSolutionRecord | None:
    """在数据库边界复制字段和必要关系。"""
    from app.persistence.user import _to_user_record

    if row is None or isinstance(row, ProblemSolutionRecord):
        return row
    return ProblemSolutionRecord(
        id=row.id,
        problem_id=row.problem_id,
        author_id=row.author_id,
        title=row.title,
        content=row.content,
        language=row.language,
        is_official=row.is_official,
        status=row.status,
        vote_count=row.vote_count,
        comment_count=row.comment_count,
        view_count=row.view_count,
        favorite_count=row.favorite_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
        author=_to_user_record(row.author),
        likes=[_to_problem_solution_like_record(item) for item in row.likes],
        favorites=[
            _to_problem_solution_favorite_record(item) for item in row.favorites
        ],
    )


def _to_problem_solution_comment_record(
    row: ProblemSolutionComment | None,
) -> ProblemSolutionCommentRecord | None:
    """在数据库边界复制字段和必要关系。"""
    from app.persistence.user import _to_user_record

    if row is None or isinstance(row, ProblemSolutionCommentRecord):
        return row
    return ProblemSolutionCommentRecord(
        id=row.id,
        solution_id=row.solution_id,
        user_id=row.user_id,
        content=row.content,
        created_at=row.created_at,
        user=_to_user_record(row.user),
    )


def _to_problem_solution_like_record(
    row: ProblemSolutionLike | None,
) -> ProblemSolutionLikeRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, ProblemSolutionLikeRecord):
        return row
    return ProblemSolutionLikeRecord(
        id=row.id,
        solution_id=row.solution_id,
        user_id=row.user_id,
        created_at=row.created_at,
    )


def _to_problem_solution_favorite_record(
    row: ProblemSolutionFavorite | None,
) -> ProblemSolutionFavoriteRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, ProblemSolutionFavoriteRecord):
        return row
    return ProblemSolutionFavoriteRecord(
        id=row.id,
        solution_id=row.solution_id,
        user_id=row.user_id,
        created_at=row.created_at,
    )


def _to_problem_tag_record(row: ProblemTag | None) -> ProblemTagRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, ProblemTagRecord):
        return row
    return ProblemTagRecord(
        id=row.id,
        slug=row.slug,
        name=row.name,
        category=row.category,
        description=row.description,
        created_at=row.created_at,
    )


def _to_problem_tag_map_record(row: ProblemTagMap | None) -> ProblemTagMapRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, ProblemTagMapRecord):
        return row
    return ProblemTagMapRecord(
        id=row.id,
        problem_id=row.problem_id,
        tag_id=row.tag_id,
        approved=row.approved,
        created_at=row.created_at,
    )

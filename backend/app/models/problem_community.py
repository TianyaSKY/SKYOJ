"""题目题解、点赞、评论、标签的 ORM 模型。"""

from datetime import datetime

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
from sqlalchemy.orm import relationship

from app.database import Base


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
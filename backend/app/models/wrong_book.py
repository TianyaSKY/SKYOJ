"""错题本 ORM：记录学生 WA / TLE / RE 等错误提交。"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class WrongBook(Base):
    """学生错题本：每道被标记为错误的题目（WA/TLE/RE）在此留一条记录。

    设计原则：
    - 每道题每个学生最多一条（通过 unique constraint 保证）。
    - 首次错题写入；后续同一题再次错题时更新 latest_attempt_at。
    - accepted=True 时自动从错题本移除（学生 ac 后不再是"错题"）。
    - reviewed=True 时标记为已复习。
    """

    __tablename__ = "wrong_books"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "problem_id",
            name="uq_wrong_books_user_problem",
        ),
        Index("ix_wrong_books_user", "user_id"),
        Index("ix_wrong_books_problem", "problem_id"),
        Index("ix_wrong_books_accepted", "accepted"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    # 首次错题时填入；每次同类错题重犯时更新。
    first_wrong_at = Column(DateTime, nullable=False)
    latest_wrong_at = Column(DateTime, nullable=False)
    # 提交 id（方便定位到具体哪次提交出错的代码）。
    submission_id = Column(
        Integer, ForeignKey("submissions.id"), nullable=True
    )
    # 是否已 AC：是则从错题本移除（学生已掌握）
    accepted = Column(Boolean, default=False, nullable=False)
    # 是否已复习
    reviewed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")
    problem = relationship("Problem")
    submission = relationship("Submission")

    def __repr__(self) -> str:
        return f"<WrongBook user={self.user_id} problem={self.problem_id} accepted={self.accepted}>"

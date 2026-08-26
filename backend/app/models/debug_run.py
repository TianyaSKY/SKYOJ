"""ACM 调试运行记录模型。"""

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time import utcnow


class DebugRun(Base):
    """ACM 题目「调试」运行记录。

    与 `Submission` 隔离：调试不计入成绩、不进入排行榜、不影响考试评分。
    """

    __tablename__ = "debug_runs"
    __table_args__ = (
        Index("ix_debug_runs_user_created", "user_id", "created_at"),
        Index("ix_debug_runs_problem_created", "problem_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=True)

    language = Column(String(50), nullable=False)
    code_content = Column(Text, nullable=False)

    status = Column(
        Enum(
            "Pending",
            "Accepted",
            "Wrong Answer",
            "Time Limit Exceeded",
            "Runtime Error",
            "Compile Error",
            "System Error",
        ),
        default="Pending",
        nullable=False,
    )

    case_name = Column(String(128), nullable=True)
    input = Column(Text, nullable=True)
    expected_output = Column(Text, nullable=True)
    actual_output = Column(Text, nullable=True)
    error_output = Column(Text, nullable=True)

    time_used_ms = Column(Integer, nullable=True)
    memory_used_kb = Column(Integer, nullable=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", lazy=True)
    problem = relationship("Problem", lazy=True)

    def __repr__(self) -> str:
        return f"<DebugRun {self.id} user={self.user_id} problem={self.problem_id} status={self.status}>"


__all__ = ["DebugRun"]

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    # 比赛类型：icpc（ICPC 罚时排行榜）/ ioi（IOI 纯分制）
    contest_type = Column(String(10), default="icpc", nullable=False)
    # 封榜时间（分钟）：比赛结束前多少分钟封榜（仅 ICPC 有效）。
    # 封榜期间 scoreboard 显示 ?，结束后自动解封。
    # None 表示不封榜（实时排行榜）。
    freeze_minutes = Column(Integer, nullable=True)
    password = Column(String(2000))
    is_visible = Column(Boolean, default=False)

    created_by = Column(Integer, ForeignKey("users.id"))
    creator = relationship("User", back_populates="created_exams")
    problems = relationship(
        "ExamProblem",
        back_populates="exam",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    submissions = relationship("Submission", back_populates="exam", lazy=True)


class ExamProblem(Base):
    __tablename__ = "exam_problems"
    __table_args__ = (Index("ix_exam_problems_exam_id", "exam_id"),)

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    display_id = Column(String(10))
    score = Column(Integer, default=100)

    exam = relationship("Exam", back_populates="problems")
    problem = relationship("Problem", back_populates="exam_problems")

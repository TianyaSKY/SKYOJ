from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
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

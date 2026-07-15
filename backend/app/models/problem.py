from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # Markdown problem description

    # Problem type: acm (standard IO), oop (unit test), kaggle (CSV scoring)
    type = Column(Enum("acm", "oop", "kaggle"), nullable=False)
    language = Column(Enum("python", "java", "c", "cpp"), nullable=False)

    # Evaluation limits
    time_limit = Column(Integer, default=1000)  # ms
    memory_limit = Column(Integer, default=128)  # mb

    test_case_path = Column(String(500))
    template_code = Column(Text)

    created_at = Column(DateTime, default=func.now())

    submissions = relationship(
        "Submission",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy=True,
    )
    exam_problems = relationship(
        "ExamProblem",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self):
        return f"<Problem {self.title}>"

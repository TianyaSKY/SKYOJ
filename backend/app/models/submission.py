from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=True)

    code_path = Column(String(500))
    code_content = Column(Text)
    language = Column(String(50))

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
    )

    score = Column(Float, default=0.0)
    output_log = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")
    exam = relationship("Exam", back_populates="submissions")

    def __repr__(self):
        return f"<Submission {self.id} by User {self.user_id}>"

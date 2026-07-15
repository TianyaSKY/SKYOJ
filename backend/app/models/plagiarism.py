from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database import Base


class PlagiarismLog(Base):
    __tablename__ = "plagiarism_logs"

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    target_submission_id = Column(
        Integer, ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True
    )
    similarity_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship(
        "Submission",
        foreign_keys=[submission_id],
        back_populates="plagiarism_log",
    )
    target_submission = relationship(
        "Submission", foreign_keys=[target_submission_id]
    )

    def __repr__(self):
        return f"<PlagiarismLog for Submission {self.submission_id}>"

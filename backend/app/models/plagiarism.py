from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class PlagiarismReport(Base):
    __tablename__ = "plagiarism_reports"
    __table_args__ = (
        Index(
            "ix_plagiarism_pair",
            "problem_id",
            "submission_a_id",
            "submission_b_id",
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    submission_a_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    submission_b_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)

    similarity_score = Column(Float, default=0.0)
    matched_blocks = Column(JSON, default=list)
    status = Column(String(20), default="pending")
    jplag_result_id = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submission_a = relationship(
        "Submission", foreign_keys=[submission_a_id], backref="plagiarism_reports_a"
    )
    submission_b = relationship(
        "Submission", foreign_keys=[submission_b_id], backref="plagiarism_reports_b"
    )

    def __repr__(self):
        return (
            f"<PlagiarismReport {self.id} "
            f"({self.submission_a_id} vs {self.submission_b_id}) "
            f"score={self.similarity_score}>"
        )

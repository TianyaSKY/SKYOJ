from datetime import datetime

from app.models.user import db


class PlagiarismLog(db.Model):
    __tablename__ = 'plagiarism_logs'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id', ondelete='CASCADE'), unique=True,
                              nullable=False)

    # The submission it was most similar to
    target_submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id', ondelete='SET NULL'), nullable=True)
    similarity_score = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    submission = db.relationship('Submission', foreign_keys=[submission_id],
                                 backref=db.backref('plagiarism_log', uselist=False))
    target_submission = db.relationship('Submission', foreign_keys=[target_submission_id])

    def __repr__(self):
        return f'<PlagiarismLog for Submission {self.submission_id}>'

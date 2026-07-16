"""剽窃检测日志的数据访问。"""

from sqlalchemy.orm import Session

from app.models.plagiarism import PlagiarismLog
from app.models.submission import Submission


class PlagiarismRepository:
    """封装剽窃检测日志的查询和删除。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list(
        self, problem_id: int | None, exam_id: int | None, min_score: float,
        page: int, page_size: int,
    ) -> tuple[list[PlagiarismLog], int, int]:
        query = self._db.query(PlagiarismLog).join(Submission, PlagiarismLog.submission_id == Submission.id)
        if problem_id is not None:
            query = query.filter(Submission.problem_id == problem_id)
        if exam_id is not None:
            query = query.filter(Submission.exam_id == exam_id)
        if min_score > 0:
            query = query.filter(PlagiarismLog.similarity_score >= min_score)
        total = query.count()
        pages = (total + page_size - 1) // page_size if total else 0
        return query.order_by(PlagiarismLog.similarity_score.desc()).offset((page - 1) * page_size).limit(page_size).all(), total, pages

    def get_by_submission_id(self, submission_id: int):
        return self._db.query(PlagiarismLog).filter_by(submission_id=submission_id).first()

    def get_by_id(self, log_id: int):
        return self._db.get(PlagiarismLog, log_id)

    def delete(self, log: PlagiarismLog) -> None:
        self._db.delete(log)
        self._db.commit()

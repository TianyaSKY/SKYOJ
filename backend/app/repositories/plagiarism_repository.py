"""查重报告数据访问。"""

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.plagiarism import PlagiarismReport


class PlagiarismRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, report_id: int) -> PlagiarismReport | None:
        return self._db.get(PlagiarismReport, report_id)

    def get_by_submission_pair(
        self, problem_id: int, sub_a: int, sub_b: int
    ) -> PlagiarismReport | None:
        a, b = (sub_a, sub_b) if sub_a < sub_b else (sub_b, sub_a)
        return (
            self._db.query(PlagiarismReport)
            .filter(
                PlagiarismReport.problem_id == problem_id,
                PlagiarismReport.submission_a_id == a,
                PlagiarismReport.submission_b_id == b,
            )
            .first()
        )

    def upsert_report(
        self,
        problem_id: int,
        sub_a: int,
        sub_b: int,
        score: float,
        blocks: list,
        status: str,
        jplag_result_id: str | None = None,
    ) -> PlagiarismReport:
        a, b = (sub_a, sub_b) if sub_a < sub_b else (sub_b, sub_a)
        existing = self.get_by_submission_pair(problem_id, a, b)
        if existing:
            existing.similarity_score = score
            existing.matched_blocks = blocks
            existing.status = status
            existing.jplag_result_id = jplag_result_id
            self._db.commit()
            self._db.refresh(existing)
            return existing
        report = PlagiarismReport(
            problem_id=problem_id,
            submission_a_id=a,
            submission_b_id=b,
            similarity_score=score,
            matched_blocks=blocks,
            status=status,
            jplag_result_id=jplag_result_id,
        )
        self._db.add(report)
        self._db.commit()
        self._db.refresh(report)
        return report

    def get_reports_for_problem(
        self, problem_id: int, min_score: float, page: int, page_size: int
    ) -> tuple[list[PlagiarismReport], int]:
        query = (
            self._db.query(PlagiarismReport)
            .filter(
                PlagiarismReport.problem_id == problem_id,
                PlagiarismReport.similarity_score >= min_score,
            )
            .order_by(PlagiarismReport.similarity_score.desc())
        )
        total = query.count()
        reports = (
            query.offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return reports, total

    def get_by_submission_id(self, submission_id: int) -> list[PlagiarismReport]:
        return (
            self._db.query(PlagiarismReport)
            .filter(
                (PlagiarismReport.submission_a_id == submission_id)
                | (PlagiarismReport.submission_b_id == submission_id)
            )
            .order_by(PlagiarismReport.similarity_score.desc())
            .all()
        )

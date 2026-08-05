"""考试领域数据访问。"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.exam import Exam, ExamProblem
from app.models.submission import Submission
from app.models.user import User


class ExamRepository:
    """封装考试、考试题目与相关提交记录的读写。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, **values) -> Exam:
        exam = Exam(**values)
        self._db.add(exam)
        self._db.commit()
        self._db.refresh(exam)
        return exam

    def get_by_id(self, exam_id: int):
        return self._db.get(Exam, exam_id)

    def list_visible_for(self, role: str) -> list[Exam]:
        query = self._db.query(Exam)
        return query.all() if role == "teacher" else query.filter_by(is_visible=True).all()

    def update(self, exam: Exam) -> Exam:
        self._db.commit()
        self._db.refresh(exam)
        return exam

    def delete(self, exam: Exam) -> None:
        self._db.delete(exam)
        self._db.commit()

    def list_problems(self, exam_id: int, ordered: bool = False) -> list[ExamProblem]:
        query = self._db.query(ExamProblem).filter_by(exam_id=exam_id)
        if ordered:
            query = query.order_by(ExamProblem.display_id)
        return query.options(joinedload(ExamProblem.problem)).all()

    def add_problem(self, exam_id: int, problem_id: int, display_id: str | None, score: int) -> ExamProblem:
        item = ExamProblem(exam_id=exam_id, problem_id=problem_id, display_id=display_id, score=score)
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return item

    def get_exam_problem(self, exam_id: int, problem_id: int):
        return self._db.query(ExamProblem).filter_by(exam_id=exam_id, problem_id=problem_id).first()

    def delete_exam_problem(self, item: ExamProblem) -> None:
        self._db.delete(item)
        self._db.commit()

    def count_problems(self, exam_id: int) -> int:
        return self._db.query(ExamProblem).filter_by(exam_id=exam_id).count()

    def count_submissions(self, exam_id: int) -> int:
        return self._db.query(Submission).filter_by(exam_id=exam_id).count()

    def get_latest_submission(self, exam_id: int, user_id: int, problem_id: int):
        return self._db.query(Submission).filter_by(exam_id=exam_id, user_id=user_id, problem_id=problem_id).order_by(Submission.created_at.desc()).first()

    def list_submissions(self, exam_id: int, problem_ids: list[int] | None = None) -> list[Submission]:
        query = self._db.query(Submission).filter(Submission.exam_id == exam_id)
        if problem_ids is not None:
            query = query.filter(Submission.problem_id.in_(problem_ids))
        return query.options(selectinload(Submission.user)).order_by(Submission.created_at.asc()).all()

    def list_submission_user_ids(self, exam_id: int) -> list[int]:
        return [value[0] for value in self._db.query(Submission.user_id).filter(Submission.exam_id == exam_id).distinct().all()]

    def list_latest_submissions(
        self,
        exam_id: int,
        *,
        user_ids: list[int] | None = None,
        problem_ids: list[int] | None = None,
    ) -> dict[tuple[int, int], Submission]:
        """一次查询拉全量提交，按 created_at 降序，返回每个 (user_id, problem_id) 的最新提交。"""
        query = self._db.query(Submission).filter(Submission.exam_id == exam_id)
        if user_ids is not None:
            query = query.filter(Submission.user_id.in_(user_ids))
        if problem_ids is not None:
            query = query.filter(Submission.problem_id.in_(problem_ids))
        result: dict[tuple[int, int], Submission] = {}
        for submission in query.order_by(Submission.created_at.desc()).all():
            result.setdefault((submission.user_id, submission.problem_id), submission)
        return result

    def list_users(self, user_ids: list[int]) -> dict[int, User]:
        """一次查询取用户，返回 id→User 字典。"""
        return {user.id: user for user in self._db.query(User).filter(User.id.in_(user_ids)).all()}

    def count_problems_batch(self, exam_ids: list[int]) -> dict[int, int]:
        """GROUP BY exam_id 统计题目数。"""
        rows = (
            self._db.query(ExamProblem.exam_id, func.count())
            .filter(ExamProblem.exam_id.in_(exam_ids))
            .group_by(ExamProblem.exam_id)
            .all()
        )
        return {exam_id: count for exam_id, count in rows}

    def count_submissions_batch(self, exam_ids: list[int]) -> dict[int, int]:
        """GROUP BY exam_id 统计提交数。"""
        rows = (
            self._db.query(Submission.exam_id, func.count())
            .filter(Submission.exam_id.in_(exam_ids))
            .group_by(Submission.exam_id)
            .all()
        )
        return {exam_id: count for exam_id, count in rows}

    def get_user(self, user_id: int):
        return self._db.get(User, user_id)

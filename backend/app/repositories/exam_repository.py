"""考试领域数据访问。"""

from datetime import datetime

from sqlalchemy.orm import Session

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
        return query.all()

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
        return query.order_by(Submission.created_at.asc()).all()

    def list_submission_user_ids(self, exam_id: int) -> list[int]:
        return [value[0] for value in self._db.query(Submission.user_id).filter(Submission.exam_id == exam_id).distinct().all()]

    def get_user(self, user_id: int):
        return self._db.get(User, user_id)

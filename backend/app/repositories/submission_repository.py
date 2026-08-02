"""提交记录数据访问。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User


class SubmissionRepository:
    """封装提交、题目和考试相关的数据访问。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_problem(self, problem_id: int):
        """查询题目。"""
        return self._db.get(Problem, problem_id)

    def get_active_exam(self, exam_id: int, now: datetime):
        """查询当前处于开放时间内的考试。"""
        return (
            self._db.query(Exam)
            .filter(Exam.id == exam_id, Exam.start_time <= now, Exam.end_time >= now)
            .first()
        )

    def create(
        self, user_id: int, problem_id: int, exam_id: int | None, language: str, code: str
    ) -> Submission:
        """创建提交记录。"""
        submission = Submission(
            user_id=user_id, problem_id=problem_id, exam_id=exam_id,
            language=language, code_content=code, status="Pending",
        )
        self._db.add(submission)
        self._db.commit()
        self._db.refresh(submission)
        return submission

    def get_by_id(self, submission_id: int):
        """查询单条提交记录。"""
        return self._db.get(Submission, submission_id)

    def list(
        self,
        problem_id: int | None,
        user_id: int | None,
        exam_id: int | None,
        status: str | None,
        username: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Submission], int, int]:
        """按条件分页查询提交记录。"""
        query = self._db.query(Submission)
        if user_id is not None:
            query = query.filter(Submission.user_id == user_id)
        if username:
            query = query.join(User).filter(User.username.like(f"%{username}%"))
        if problem_id is not None:
            query = query.filter(Submission.problem_id == problem_id)
        if exam_id is not None:
            query = query.filter(Submission.exam_id == exam_id)
        if status:
            query = query.filter(Submission.status == status)
        total = query.count()
        pages = (total + page_size - 1) // page_size if total else 0
        return (
            query.order_by(Submission.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all(),
            total,
            pages,
        )

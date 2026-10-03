"""exam 数据库模型、仓储与映射。"""

from __future__ import annotations

from app.persistence.database import Base
from app.persistence.unit_of_work import UnitOfWork
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Session, joinedload, relationship, selectinload
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.persistence.submission import Submission
    from app.persistence.user import User
    from app.services.exam import ExamDetail, ExamListItem, ExamProblemItem


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    # 比赛类型：icpc（ICPC 罚时排行榜）/ ioi（IOI 纯分制）
    contest_type = Column(String(10), default="icpc", nullable=False)
    # 封榜时间（分钟）：比赛结束前多少分钟封榜（仅 ICPC 有效）。
    # 封榜期间 scoreboard 显示 ?，结束后自动解封。
    # None 表示不封榜（实时排行榜）。
    freeze_minutes = Column(Integer, nullable=True)
    password = Column(String(2000))
    is_visible = Column(Boolean, default=False)

    created_by = Column(Integer, ForeignKey("users.id"))
    creator = relationship("User", back_populates="created_exams")
    problems = relationship(
        "ExamProblem",
        back_populates="exam",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    submissions = relationship("Submission", back_populates="exam", lazy=True)


class ExamProblem(Base):
    __tablename__ = "exam_problems"
    __table_args__ = (Index("ix_exam_problems_exam_id", "exam_id"),)

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    display_id = Column(String(10))
    score = Column(Integer, default=100)

    exam = relationship("Exam", back_populates="problems")
    problem = relationship("Problem", back_populates="exam_problems")


class ExamRepository:
    """封装考试、考试题目与相关提交记录的读写。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self.unit_of_work = UnitOfWork(db)

    def create(self, **values) -> Exam:
        exam = Exam(**values)
        self._db.add(exam)
        self._db.flush()
        self._db.refresh(exam)
        return exam

    def get_by_id(self, exam_id: int):
        return self._db.get(Exam, exam_id)

    def list_visible_for(self, role: str) -> list[Exam]:
        query = self._db.query(Exam)
        return (
            query.all() if role == "teacher" else query.filter_by(is_visible=True).all()
        )

    def update(self, exam: Exam) -> Exam:
        self._db.flush()
        self._db.refresh(exam)
        return exam

    def delete(self, exam: Exam) -> None:
        self._db.delete(exam)
        self._db.flush()

    def list_problems(self, exam_id: int, ordered: bool = False) -> list[ExamProblem]:
        query = self._db.query(ExamProblem).filter_by(exam_id=exam_id)
        if ordered:
            query = query.order_by(ExamProblem.display_id)
        return query.options(joinedload(ExamProblem.problem)).all()

    def add_problem(
        self, exam_id: int, problem_id: int, display_id: str | None, score: int
    ) -> ExamProblem:
        item = ExamProblem(
            exam_id=exam_id, problem_id=problem_id, display_id=display_id, score=score
        )
        self._db.add(item)
        self._db.flush()
        self._db.refresh(item)
        return item

    def get_exam_problem(self, exam_id: int, problem_id: int):
        return (
            self._db.query(ExamProblem)
            .filter_by(exam_id=exam_id, problem_id=problem_id)
            .first()
        )

    def delete_exam_problem(self, item: ExamProblem) -> None:
        self._db.delete(item)
        self._db.flush()

    def count_problems(self, exam_id: int) -> int:
        return self._db.query(ExamProblem).filter_by(exam_id=exam_id).count()

    def count_submissions(self, exam_id: int) -> int:

        from app.persistence.submission import Submission
        return self._db.query(Submission).filter_by(exam_id=exam_id).count()

    def get_latest_submission(self, exam_id: int, user_id: int, problem_id: int):

        from app.persistence.submission import Submission
        return (
            self._db.query(Submission)
            .filter_by(exam_id=exam_id, user_id=user_id, problem_id=problem_id)
            .order_by(Submission.created_at.desc())
            .first()
        )

    def list_submissions(
        self, exam_id: int, problem_ids: list[int] | None = None
    ) -> list[Submission]:

        from app.persistence.submission import Submission
        query = self._db.query(Submission).filter(Submission.exam_id == exam_id)
        if problem_ids is not None:
            query = query.filter(Submission.problem_id.in_(problem_ids))
        return (
            query.options(selectinload(Submission.user))
            .order_by(Submission.created_at.asc())
            .all()
        )

    def list_submission_user_ids(self, exam_id: int) -> list[int]:

        from app.persistence.submission import Submission
        return [
            value[0]
            for value in self._db.query(Submission.user_id)
            .filter(Submission.exam_id == exam_id)
            .distinct()
            .all()
        ]

    def list_latest_submissions(
        self,
        exam_id: int,
        *,
        user_ids: list[int] | None = None,
        problem_ids: list[int] | None = None,
    ) -> dict[tuple[int, int], Submission]:
        """一次查询拉全量提交，按 created_at 降序，返回每个 (user_id, problem_id) 的最新提交。"""

        from app.persistence.submission import Submission
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

        from app.persistence.user import User
        return {
            user.id: user
            for user in self._db.query(User).filter(User.id.in_(user_ids)).all()
        }

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

        from app.persistence.submission import Submission
        rows = (
            self._db.query(Submission.exam_id, func.count())
            .filter(Submission.exam_id.in_(exam_ids))
            .group_by(Submission.exam_id)
            .all()
        )
        return {exam_id: count for exam_id, count in rows}

    def get_user(self, user_id: int):

        from app.persistence.user import User
        return self._db.get(User, user_id)


def from_exam_orm(exam, *, problem_count: int, submission_count: int) -> ExamListItem:
    """考试 ORM → 列表项（题目/提交数由调用方从批量方法取得）。"""

    from app.services.exam import ExamListItem
    return ExamListItem(
        id=exam.id,
        title=exam.title,
        description=exam.description or "",
        start_time=exam.start_time,
        end_time=exam.end_time,
        contest_type=exam.contest_type or "icpc",
        freeze_minutes=exam.freeze_minutes,
        is_visible=exam.is_visible,
        created_by=exam.created_by,
        problem_count=problem_count,
        submission_count=submission_count,
        has_password=bool(exam.password),
    )


def from_exam_detail_orm(exam, problems) -> ExamDetail:
    """考试 ORM + 题目列表 → 详情（problems 需已预取 problem 关系）。"""

    from app.services.exam import ExamDetail, ExamProblemItem
    return ExamDetail(
        id=exam.id,
        title=exam.title,
        description=exam.description or "",
        start_time=exam.start_time,
        end_time=exam.end_time,
        contest_type=exam.contest_type or "icpc",
        freeze_minutes=exam.freeze_minutes,
        is_visible=exam.is_visible,
        created_by=exam.created_by,
        has_password=bool(exam.password),
        problems=[
            ExamProblemItem(item.problem_id, item.display_id, item.score, item.problem.title)
            for item in problems
        ],
    )

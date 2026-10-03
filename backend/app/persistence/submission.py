"""submission 数据库模型、仓储与映射。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    case,
    func,
    update,
)
from sqlalchemy.orm import Session, relationship, selectinload

from app.core.json import JsonValue
from app.core.time import utcnow
from app.persistence.database import Base
from app.persistence.problem import ProblemRecord
from app.persistence.user import UserRecord


@dataclass
class SubmissionRecord:
    """Submission 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    user_id: int
    problem_id: int
    exam_id: int | None
    code_path: str | None
    code_content: str | None
    language: str | None
    status: str | None
    score: float | None
    output_log: str | None
    case_results: list[dict[str, JsonValue]] | None
    created_at: datetime | None
    user: UserRecord | None
    problem: ProblemRecord | None


@dataclass
class DebugRunRecord:
    """DebugRun 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    user_id: int
    problem_id: int
    exam_id: int | None
    language: str
    code_content: str
    status: str
    case_name: str | None
    input: str | None
    expected_output: str | None
    actual_output: str | None
    error_output: str | None
    time_used_ms: int | None
    memory_used_kb: int | None
    created_at: datetime
    finished_at: datetime | None


@dataclass
class PlagiarismReportRecord:
    """PlagiarismReport 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    problem_id: int
    submission_a_id: int
    submission_b_id: int
    similarity_score: float | None
    matched_blocks: list[dict[str, JsonValue]] | None
    status: str | None
    jplag_result_id: str | None
    created_at: datetime | None
    updated_at: datetime | None
    submission_a: SubmissionRecord | None
    submission_b: SubmissionRecord | None


@dataclass(frozen=True)
class ProblemSubmissionCounts:
    problem_id: int
    title: str
    total: int
    accepted: int


@dataclass(frozen=True)
class DailySubmissionCount:
    date: str
    count: int


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submissions_exam_problem_user", "exam_id", "problem_id", "user_id"),
        Index("ix_submissions_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=True)

    # 新记录：空串表示内联文本，非空表示存储客户端生成的附件路径；NULL 为旧记录。
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
    # 逐点判题结果。结构：[{"case_name", "status", "time_used_ms", "memory_used_kb", "input_data", "expected_output", "actual_output", "error_output"}]
    # 仅 ACM 模式写入；OOP / Kaggle 留空列表。
    case_results = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")
    exam = relationship("Exam", back_populates="submissions")

    def __repr__(self):
        return f"<Submission {self.id} by User {self.user_id}>"


class DebugRun(Base):
    """ACM 题目「调试」运行记录。

    与 `Submission` 隔离：调试不计入成绩、不进入排行榜、不影响考试评分。
    """

    __tablename__ = "debug_runs"
    __table_args__ = (
        Index("ix_debug_runs_user_created", "user_id", "created_at"),
        Index("ix_debug_runs_problem_created", "problem_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=True)

    language = Column(String(50), nullable=False)
    code_content = Column(Text, nullable=False)

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
        nullable=False,
    )

    case_name = Column(String(128), nullable=True)
    input = Column(Text, nullable=True)
    expected_output = Column(Text, nullable=True)
    actual_output = Column(Text, nullable=True)
    error_output = Column(Text, nullable=True)

    time_used_ms = Column(Integer, nullable=True)
    memory_used_kb = Column(Integer, nullable=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", lazy=True)
    problem = relationship("Problem", lazy=True)

    def __repr__(self) -> str:
        return f"<DebugRun {self.id} user={self.user_id} problem={self.problem_id} status={self.status}>"


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


class SubmissionRepository:
    """封装提交、题目和考试相关的数据访问。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_problem(self, problem_id: int):
        """查询题目。"""
        from app.persistence.problem import Problem, _to_problem_record

        return _to_problem_record(self._db.get(Problem, problem_id))

    def get_active_exam(self, exam_id: int, now: datetime):
        """查询当前处于开放时间内的考试。"""
        from app.persistence.exam import Exam, _to_exam_record

        return _to_exam_record(
            self._db.query(Exam)
            .filter(Exam.id == exam_id, Exam.start_time <= now, Exam.end_time >= now)
            .first()
        )

    def get_exam_problem(self, exam_id: int, problem_id: int):
        """查询考试是否包含指定题目。"""
        from app.persistence.exam import ExamProblem, _to_exam_problem_record

        return _to_exam_problem_record(
            self._db.query(ExamProblem)
            .filter(
                ExamProblem.exam_id == exam_id, ExamProblem.problem_id == problem_id
            )
            .first()
        )

    def create(
        self,
        user_id: int,
        problem_id: int,
        exam_id: int | None,
        language: str,
        code: str,
        *,
        code_path: str = "",
    ) -> SubmissionRecord:
        """创建提交记录。"""
        submission = Submission(
            user_id=user_id,
            problem_id=problem_id,
            exam_id=exam_id,
            language=language,
            code_content=code,
            code_path=code_path,
            status="Pending",
        )
        self._db.add(submission)
        self._db.flush()
        self._db.refresh(submission)
        return _to_submission_record(submission)

    def get_by_id(self, submission_id: int):
        """查询单条提交记录。"""
        return _to_submission_record(self._db.get(Submission, submission_id))

    def update_result(
        self,
        submission_id: int,
        *,
        status: str,
        score: float,
        output_log: str,
        case_results: list[dict] | None = None,
    ) -> None:
        """更新判题结果；不提交事务，由调用方 commit。

        case_results 仅 ACM 模式写入，结构与 ``Submission.case_results`` JSON 列一致。
        """
        values: dict = {"status": status, "score": score, "output_log": output_log}
        if case_results is not None:
            values["case_results"] = case_results
        self._db.execute(
            update(Submission).where(Submission.id == submission_id).values(**values)
        )

    def list_all(
        self,
        problem_id: int | None,
        user_id: int | None,
        exam_id: int | None,
        status: str | None,
        username: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SubmissionRecord], int, int]:
        """按条件分页查询提交记录。"""

        from app.persistence.user import User

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
            [
                _to_submission_record(row)
                for row in (
                    query.options(
                        selectinload(Submission.user), selectinload(Submission.problem)
                    )
                    .order_by(Submission.created_at.desc(), Submission.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                    .all()
                )
            ],
            total,
            pages,
        )

    def list_accepted_for_plagiarism(self, problem_id: int) -> list[SubmissionRecord]:
        """查询有效代码，数据库访问留在仓储内。"""
        return [
            _to_submission_record(row)
            for row in (
                self._db.query(Submission)
                .filter(
                    Submission.problem_id == problem_id,
                    Submission.status == "Accepted",
                    Submission.code_content.isnot(None),
                )
                .options(
                    selectinload(Submission.user), selectinload(Submission.problem)
                )
                .all()
            )
        ]

    def get_global_counts(self) -> tuple[int, int, int]:

        from app.persistence.problem import Problem

        total, accepted = self._db.query(
            func.count(Submission.id),
            func.coalesce(
                func.sum(case((Submission.status == "Accepted", 1), else_=0)), 0
            ),
        ).one()
        return total, int(accepted), self._db.query(func.count(Problem.id)).scalar()

    def get_problem_submission_counts(self) -> list[ProblemSubmissionCounts]:

        from app.persistence.problem import Problem

        rows = (
            self._db.query(
                Problem.id,
                Problem.title,
                func.count(Submission.id),
                func.sum(case((Submission.status == "Accepted", 1), else_=0)),
            )
            .join(Submission, Submission.problem_id == Problem.id)
            .group_by(Problem.id, Problem.title)
            .order_by(Problem.id)
            .all()
        )
        return [
            ProblemSubmissionCounts(pid, title, total, int(accepted))
            for pid, title, total, accepted in rows
        ]

    def get_daily_submission_counts(
        self, since: datetime
    ) -> list[DailySubmissionCount]:

        day = func.date(Submission.created_at)
        rows = (
            self._db.query(day, func.count(Submission.id))
            .filter(Submission.created_at >= since)
            .group_by(day)
            .order_by(day)
            .all()
        )
        return [DailySubmissionCount(str(date), count) for date, count in rows]


class DebugRunRepository:
    """封装 `debug_runs` 表的增改查。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: int,
        problem_id: int,
        exam_id: Optional[int],
        language: str,
        code: str,
    ) -> DebugRunRecord:
        """创建一条调试记录，初始状态为 Pending。"""
        row = DebugRun(
            user_id=user_id,
            problem_id=problem_id,
            exam_id=exam_id,
            language=language,
            code_content=code,
            status="Pending",
        )
        self._db.add(row)
        self._db.flush()
        self._db.refresh(row)
        return _to_debug_run_record(row)

    def get_by_id(self, debug_run_id: int) -> Optional[DebugRunRecord]:
        """查询单条调试记录。"""
        return _to_debug_run_record(self._db.get(DebugRun, debug_run_id))

    def finish(
        self,
        debug_run_id: int,
        *,
        status: str,
        case_name: Optional[str] = None,
        input_data: Optional[str] = None,
        expected_output: Optional[str] = None,
        actual_output: Optional[str] = None,
        error_output: Optional[str] = None,
        time_used_ms: Optional[int] = None,
        memory_used_kb: Optional[int] = None,
    ) -> None:
        """写入最终结果。"""
        values: dict[str, object] = {
            "status": status,
            "finished_at": utcnow(),
        }
        if case_name is not None:
            values["case_name"] = case_name
        if input_data is not None:
            values["input"] = input_data
        if expected_output is not None:
            values["expected_output"] = expected_output
        if actual_output is not None:
            values["actual_output"] = actual_output
        if error_output is not None:
            values["error_output"] = error_output
        if time_used_ms is not None:
            values["time_used_ms"] = time_used_ms
        if memory_used_kb is not None:
            values["memory_used_kb"] = memory_used_kb
        self._db.query(DebugRun).filter(DebugRun.id == debug_run_id).update(values)
        self._db.flush()

    def get_problem(self, problem_id: int):
        from app.persistence.problem import _to_problem_record

        return _to_problem_record(
            SubmissionRepository(self._db).get_problem(problem_id)
        )

    def get_active_exam(self, exam_id: int, now: datetime):
        from app.persistence.exam import _to_exam_record

        return _to_exam_record(
            SubmissionRepository(self._db).get_active_exam(exam_id, now)
        )

    def get_exam_problem(self, exam_id: int, problem_id: int):
        """查询调试题目是否属于当前考试。"""
        return SubmissionRepository(self._db).get_exam_problem(exam_id, problem_id)


class PlagiarismRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, report_id: int) -> PlagiarismReportRecord | None:
        return _to_plagiarism_report_record(self._db.get(PlagiarismReport, report_id))

    def get_by_submission_pair(
        self, problem_id: int, sub_a: int, sub_b: int
    ) -> PlagiarismReportRecord | None:
        a, b = (sub_a, sub_b) if sub_a < sub_b else (sub_b, sub_a)
        return _to_plagiarism_report_record(
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
    ) -> PlagiarismReportRecord:
        a, b = (sub_a, sub_b) if sub_a < sub_b else (sub_b, sub_a)
        existing = self.get_by_submission_pair(problem_id, a, b)
        if existing:
            existing = self._db.get(PlagiarismReport, existing.id)
            existing.similarity_score = score
            existing.matched_blocks = blocks
            existing.status = status
            existing.jplag_result_id = jplag_result_id
            self._db.flush()
            self._db.refresh(existing)
            return _to_plagiarism_report_record(existing)
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
        self._db.flush()
        self._db.refresh(report)
        return _to_plagiarism_report_record(report)

    def get_reports_for_problem(
        self, problem_id: int, min_score: float, page: int, page_size: int
    ) -> tuple[list[PlagiarismReportRecord], int]:
        query = (
            self._db.query(PlagiarismReport)
            .filter(
                PlagiarismReport.problem_id == problem_id,
                PlagiarismReport.similarity_score >= min_score,
            )
            .order_by(PlagiarismReport.similarity_score.desc())
        )
        total = query.count()
        reports = query.offset((page - 1) * page_size).limit(page_size).all()
        return ([_to_plagiarism_report_record(row) for row in (reports)], total)

    def get_by_submission_id(self, submission_id: int) -> list[PlagiarismReportRecord]:
        return [
            _to_plagiarism_report_record(row)
            for row in (
                self._db.query(PlagiarismReport)
                .filter(
                    (PlagiarismReport.submission_a_id == submission_id)
                    | (PlagiarismReport.submission_b_id == submission_id)
                )
                .order_by(PlagiarismReport.similarity_score.desc())
                .all()
            )
        ]


def _to_submission_record(row: Submission | None) -> SubmissionRecord | None:
    """在数据库边界复制字段和必要关系。"""
    from app.persistence.problem import _to_problem_record
    from app.persistence.user import _to_user_record

    if row is None or isinstance(row, SubmissionRecord):
        return row
    return SubmissionRecord(
        id=row.id,
        user_id=row.user_id,
        problem_id=row.problem_id,
        exam_id=row.exam_id,
        code_path=row.code_path,
        code_content=row.code_content,
        language=row.language,
        status=row.status,
        score=row.score,
        output_log=row.output_log,
        case_results=deepcopy(row.case_results),
        created_at=row.created_at,
        user=_to_user_record(row.user),
        problem=_to_problem_record(row.problem),
    )


def _to_debug_run_record(row: DebugRun | None) -> DebugRunRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, DebugRunRecord):
        return row
    return DebugRunRecord(
        id=row.id,
        user_id=row.user_id,
        problem_id=row.problem_id,
        exam_id=row.exam_id,
        language=row.language,
        code_content=row.code_content,
        status=row.status,
        case_name=row.case_name,
        input=row.input,
        expected_output=row.expected_output,
        actual_output=row.actual_output,
        error_output=row.error_output,
        time_used_ms=row.time_used_ms,
        memory_used_kb=row.memory_used_kb,
        created_at=row.created_at,
        finished_at=row.finished_at,
    )


def _to_plagiarism_report_record(
    row: PlagiarismReport | None,
) -> PlagiarismReportRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, PlagiarismReportRecord):
        return row
    return PlagiarismReportRecord(
        id=row.id,
        problem_id=row.problem_id,
        submission_a_id=row.submission_a_id,
        submission_b_id=row.submission_b_id,
        similarity_score=row.similarity_score,
        matched_blocks=deepcopy(row.matched_blocks),
        status=row.status,
        jplag_result_id=row.jplag_result_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        submission_a=_to_submission_record(row.submission_a),
        submission_b=_to_submission_record(row.submission_b),
    )

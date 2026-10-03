"""problem 数据库模型、仓储与映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Session, relationship

from app.persistence.database import Base


@dataclass
class ProblemRecord:
    """Problem 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    title: str
    content: str
    type: str
    language: str
    time_limit: int | None
    memory_limit: int | None
    test_case_path: str | None
    template_code: str | None
    created_at: datetime | None


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # Markdown problem description

    # Problem type: acm (standard IO), oop (unit test), kaggle (CSV scoring)
    type = Column(Enum("acm", "oop", "kaggle"), nullable=False)
    language = Column(Enum("python", "java", "c", "cpp"), nullable=False)

    # Evaluation limits
    time_limit = Column(Integer, default=1000)  # ms
    memory_limit = Column(Integer, default=128)  # mb

    test_case_path = Column(String(500))
    template_code = Column(Text)

    created_at = Column(DateTime, default=func.now())

    submissions = relationship(
        "Submission",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy=True,
    )
    exam_problems = relationship(
        "ExamProblem",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy=True,
    )
    solutions = relationship(
        "ProblemSolution",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self):
        return f"<Problem {self.title}>"


@dataclass(frozen=True)
class ProblemQuery:
    """题目查询条件，过滤在计数和分页之前执行。"""

    tag_id: int | None = None
    visible_ids: frozenset[int] | None = None
    problem_type: str | None = None


class ProblemRepository:
    """problems 表读写（草稿应用场景）。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, problem_id: int) -> Optional[ProblemRecord]:
        """按主键查询题目。"""
        return _to_problem_record(self._db.get(Problem, problem_id))

    def create(
        self,
        *,
        title: str,
        content: str,
        language: str,
        problem_type: str,
        time_limit: int,
        memory_limit: int,
        template_code: str = "",
    ) -> ProblemRecord:
        """创建正式题目。"""
        problem = Problem(
            title=title,
            content=content,
            language=language,
            type=problem_type,
            time_limit=time_limit,
            memory_limit=memory_limit,
            template_code=template_code or "",
        )
        self._db.add(problem)
        self._db.flush()
        self._db.refresh(problem)
        return _to_problem_record(problem)

    def list_all(
        self,
        page: int | None = None,
        page_size: int | None = None,
        *,
        filters: ProblemQuery | None = None,
    ) -> tuple[list[ProblemRecord], int | None]:
        """按创建顺序倒序查询题目，必要时在数据库侧分页。"""
        query = self._db.query(Problem).order_by(Problem.id.desc())
        if filters is not None:
            if filters.problem_type is not None:
                query = query.filter(Problem.type == filters.problem_type)
            if filters.tag_id is not None:
                from app.persistence.community import ProblemTagMap

                query = query.filter(
                    self._db.query(ProblemTagMap.id)
                    .filter(
                        ProblemTagMap.problem_id == Problem.id,
                        ProblemTagMap.tag_id == filters.tag_id,
                        ProblemTagMap.approved.is_(True),
                    )
                    .exists()
                )
            if filters.visible_ids is not None:
                query = query.filter(Problem.id.in_(filters.visible_ids))
        if page is None or page_size is None:
            return ([_to_problem_record(row) for row in (query.all())], None)

        total = query.count()
        problems = query.offset((page - 1) * page_size).limit(page_size).all()
        return ([_to_problem_record(row) for row in (problems)], total)

    def update(self, problem: ProblemRecord) -> ProblemRecord:
        """持久化题目更新。"""
        row = self._db.get(Problem, problem.id)
        row.title = problem.title
        row.content = problem.content
        row.type = problem.type
        row.language = problem.language
        row.time_limit = problem.time_limit
        row.memory_limit = problem.memory_limit
        row.template_code = problem.template_code
        row.test_case_path = problem.test_case_path
        problem = row
        self._db.flush()
        self._db.refresh(problem)
        return _to_problem_record(problem)

    def delete(self, problem: ProblemRecord) -> None:
        """删除指定题目。"""
        self._db.delete(self._db.get(Problem, problem.id))
        self._db.flush()


def _to_problem_record(row: Problem | None) -> ProblemRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, ProblemRecord):
        return row
    return ProblemRecord(
        id=row.id,
        title=row.title,
        content=row.content,
        type=row.type,
        language=row.language,
        time_limit=row.time_limit,
        memory_limit=row.memory_limit,
        test_case_path=row.test_case_path,
        template_code=row.template_code,
        created_at=row.created_at,
    )

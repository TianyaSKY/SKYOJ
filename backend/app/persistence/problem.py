"""problem 数据库模型、仓储与映射。"""

from __future__ import annotations

from app.persistence.database import Base
from app.persistence.unit_of_work import UnitOfWork
from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Session, relationship
from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from app.services.problem import ProblemDetail, ProblemListItem


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


class ProblemRepository:
    """problems 表读写（草稿应用场景）。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self.unit_of_work = UnitOfWork(db)

    def get_by_id(self, problem_id: int) -> Optional[Problem]:
        """按主键查询题目。"""
        return self._db.get(Problem, problem_id)

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
    ) -> Problem:
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
        return problem

    def list_all(
        self, page: int | None = None, page_size: int | None = None
    ) -> tuple[list[Problem], int | None]:
        """按创建顺序倒序查询题目，必要时在数据库侧分页。"""
        query = self._db.query(Problem).order_by(Problem.id.desc())
        if page is None or page_size is None:
            return query.all(), None

        total = query.count()
        problems = query.offset((page - 1) * page_size).limit(page_size).all()
        return problems, total

    def update(self, problem: Problem) -> Problem:
        """持久化题目更新。"""
        self._db.flush()
        self._db.refresh(problem)
        return problem

    def delete(self, problem: Problem) -> None:
        """删除指定题目。"""
        self._db.delete(problem)
        self._db.flush()

    def list_problem_ids_by_tag(self, tag_id: int) -> list[int]:
        from app.persistence.community import (
            ProblemCommunityRepository,
        )

        return ProblemCommunityRepository(self._db).list_problem_ids_by_tag(tag_id)


def from_problem_orm(problem, *, with_content: bool = False) -> ProblemListItem | ProblemDetail:
    """题目 ORM → 列表项或详情。"""

    from app.services.problem import ProblemDetail, ProblemListItem
    if with_content:
        return ProblemDetail(
            id=problem.id,
            title=problem.title,
            content=problem.content,
            problem_type=problem.type,
            language=problem.language,
            time_limit=problem.time_limit,
            memory_limit=problem.memory_limit,
            template_code=problem.template_code or "",
            test_case_path=problem.test_case_path,
            created_at=problem.created_at,
        )
    return ProblemListItem(
        id=problem.id,
        title=problem.title,
        problem_type=problem.type,
        language=problem.language,
        time_limit=problem.time_limit,
        memory_limit=problem.memory_limit,
    )

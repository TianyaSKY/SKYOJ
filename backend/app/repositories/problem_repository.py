"""题目数据访问。"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.problem import Problem


class ProblemRepository:
    """problems 表读写（草稿应用场景）。"""

    def __init__(self, db: Session) -> None:
        self._db = db

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
        self._db.commit()
        self._db.refresh(problem)
        return problem

    def list(
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
        self._db.commit()
        self._db.refresh(problem)
        return problem

    def delete(self, problem: Problem) -> None:
        """删除指定题目。"""
        self._db.delete(problem)
        self._db.commit()

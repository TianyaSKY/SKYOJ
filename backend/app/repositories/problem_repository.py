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

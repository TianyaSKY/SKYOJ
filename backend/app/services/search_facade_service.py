"""题目关键词搜索业务编排。"""

from loguru import logger

from app.domain.problem import ProblemDetail
from app.mappers import from_problem_orm
from app.repositories.search_repository import SearchRepository


class SearchFacadeService:
    """编排题目关键词搜索和历史记录。"""

    def __init__(self, repository: SearchRepository) -> None:
        self._repository = repository

    def search(self, user_id: int, query: str, top_k: int) -> list[ProblemDetail]:
        if not query:
            return []
        try:
            self._repository.add_history(user_id, query)
        except Exception:
            logger.exception("保存搜索历史失败，用户 ID：{}", user_id)
        return [
            from_problem_orm(problem, with_content=True)
            for problem in self._repository.search_problems(query, top_k)
        ]

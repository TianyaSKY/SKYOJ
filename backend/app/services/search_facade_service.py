"""题目关键词搜索业务编排。"""

from loguru import logger

from app.repositories.search_repository import SearchRepository


class SearchFacadeService:
    """编排题目关键词搜索和历史记录。"""

    def __init__(self, repository: SearchRepository) -> None:
        self._repository = repository

    def search(self, user_id: int, query: str, top_k: int) -> list[dict]:
        if not query:
            return []
        try:
            self._repository.add_history(user_id, query)
        except Exception:
            logger.exception("保存搜索历史失败，用户 ID：{}", user_id)
        return [self._to_dict(problem) for problem in self._repository.search_problems(query, top_k)]

    @staticmethod
    def _to_dict(problem) -> dict:
        return {"id": problem.id, "title": problem.title, "content": problem.content, "type": problem.type, "language": problem.language, "time_limit": problem.time_limit, "memory_limit": problem.memory_limit}

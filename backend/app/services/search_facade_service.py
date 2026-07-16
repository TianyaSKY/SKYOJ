"""搜索业务编排。"""

from loguru import logger

from app.repositories.search_repository import SearchRepository
from app.domain.errors import InvalidStateError, PermissionDeniedError
from app.utils.feature_flags import ENABLE_SEMANTIC_SEARCH


class SearchFacadeService:
    """编排普通搜索、语义搜索和历史记录。"""

    def __init__(self, repository: SearchRepository, semantic_service) -> None:
        self._repository = repository
        self._semantic_service = semantic_service

    def search(self, user_id: int, query: str, mode: str, top_k: int) -> list[dict]:
        if not query:
            return []
        try:
            self._repository.add_history(user_id, query)
        except Exception:
            logger.exception("保存搜索历史失败，用户 ID：{}", user_id)
        if mode == "semantic" and ENABLE_SEMANTIC_SEARCH:
            return self._semantic_service.search(query, top_k=top_k)
        return [self._to_dict(problem) for problem in self._repository.search_problems(query, top_k)]

    def rebuild(self, requester_role: str) -> None:
        """重建语义索引，仅允许教师在功能启用时执行。"""
        if requester_role != "teacher":
            raise PermissionDeniedError("没有教师权限")
        if not ENABLE_SEMANTIC_SEARCH:
            raise InvalidStateError("语义搜索服务当前未启用")
        self._semantic_service.rebuild_index()

    @staticmethod
    def _to_dict(problem) -> dict:
        return {"id": problem.id, "title": problem.title, "content": problem.content, "type": problem.type, "language": problem.language, "time_limit": problem.time_limit, "memory_limit": problem.memory_limit}

"""search 业务参数、结果与服务。"""

from __future__ import annotations

from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.persistence.unit_of_work import UnitOfWork
from app.persistence.user import SearchRepository
from app.services.problem import ProblemDetail, to_problem_result
from loguru import logger


class SearchFacadeService:
    """编排题目关键词搜索和历史记录。"""

    def __init__(
        self,
        repository: SearchRepository,
        test_case_storage: ProblemTestCaseStorageClient | None = None,
        *,
        uow: UnitOfWork,
    ) -> None:
        self._uow = uow
        self._repository = repository
        self._test_case_storage = test_case_storage or ProblemTestCaseStorageClient()

    def search(
        self, user_id: int, query: str, top_k: int, requester_role: str
    ) -> list[ProblemDetail]:
        if not query:
            return []
        try:
            self._repository.add_history(user_id, query)
            self._uow.commit()
        except Exception:
            self._uow.rollback()
            logger.exception("保存搜索历史失败，用户 ID：{}", user_id)
        visible_ids = (
            None if requester_role == "teacher"
            else self._test_case_storage.list_problem_ids_with_test_cases()
        )
        problems = self._repository.search_problems(query, top_k, visible_ids=visible_ids)
        return [to_problem_result(problem, with_content=True) for problem in problems]

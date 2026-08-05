"""题目关键词搜索业务编排。"""

from loguru import logger

from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.domain.problem import ProblemDetail
from app.mappers import from_problem_orm
from app.repositories.search_repository import SearchRepository


class SearchFacadeService:
    """编排题目关键词搜索和历史记录。"""

    def __init__(
        self,
        repository: SearchRepository,
        test_case_storage: ProblemTestCaseStorageClient | None = None,
    ) -> None:
        self._repository = repository
        self._test_case_storage = test_case_storage or ProblemTestCaseStorageClient()

    def search(
        self, user_id: int, query: str, top_k: int, requester_role: str
    ) -> list[ProblemDetail]:
        if not query:
            return []
        try:
            self._repository.add_history(user_id, query)
        except Exception:
            logger.exception("保存搜索历史失败，用户 ID：{}", user_id)
        problems = self._repository.search_problems(query, top_k)
        if requester_role != "teacher":
            problems = [
                problem
                for problem in problems
                if self._test_case_storage.has_test_cases(problem.id)
            ]
        return [
            from_problem_orm(problem, with_content=True) for problem in problems
        ]

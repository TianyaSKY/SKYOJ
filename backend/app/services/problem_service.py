"""题目领域的业务服务。"""

from app.domain.errors import ResourceNotFoundError
from app.domain.problem import (
    CreateProblemParams,
    PaginatedProblems,
    ProblemDetail,
    ProblemListItem,
    UpdateProblemParams,
    UploadTestCasesParams,
)
from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.domain.errors import PermissionDeniedError
from app.repositories.problem_repository import ProblemRepository


class ProblemService:
    """编排题目的创建、查询、更新和删除业务。"""

    def __init__(
        self,
        problem_repository: ProblemRepository,
        test_case_storage: ProblemTestCaseStorageClient | None = None,
    ) -> None:
        self._problem_repository = problem_repository
        self._test_case_storage = test_case_storage or ProblemTestCaseStorageClient()

    def create_problem(
        self, requester_role: str, params: CreateProblemParams
    ) -> ProblemDetail:
        """创建题目并返回其详情。"""
        self._require_teacher(requester_role)
        problem = self._problem_repository.create(
            title=params.title,
            content=params.content,
            language=params.language,
            problem_type=params.problem_type,
            time_limit=params.time_limit,
            memory_limit=params.memory_limit,
            template_code=params.template_code,
        )
        return self._to_detail(problem)

    def list_problems(
        self, page: int | None = None, page_size: int | None = None
    ) -> list[ProblemListItem] | PaginatedProblems:
        """查询题目列表，并在指定页码时返回分页结果。"""
        problems, total = self._problem_repository.list(page=page, page_size=page_size)
        items = [self._to_list_item(problem) for problem in problems]
        if page is None or page_size is None:
            return items

        return PaginatedProblems(
            total=total or 0,
            page=page,
            page_size=page_size,
            problems=items,
        )

    def get_problem(self, problem_id: int) -> ProblemDetail:
        """获取题目详情。"""
        return self._to_detail(self._require_problem(problem_id))

    def update_problem(
        self, requester_role: str, problem_id: int, params: UpdateProblemParams
    ) -> ProblemDetail:
        """更新题目的已提供字段。"""
        self._require_teacher(requester_role)
        problem = self._require_problem(problem_id)
        for attribute, value in (
            ("title", params.title),
            ("content", params.content),
            ("language", params.language),
            ("type", params.problem_type),
            ("time_limit", params.time_limit),
            ("memory_limit", params.memory_limit),
            ("template_code", params.template_code),
        ):
            if value is not None:
                setattr(problem, attribute, value)

        return self._to_detail(self._problem_repository.update(problem))

    def delete_problem(self, requester_role: str, problem_id: int) -> None:
        """删除题目记录。"""
        self._require_teacher(requester_role)
        problem = self._require_problem(problem_id)
        self._test_case_storage.delete_problem_directory(problem_id)
        self._problem_repository.delete(problem)

    def upload_test_cases(
        self, requester_role: str, params: UploadTestCasesParams
    ) -> list[str]:
        """上传并解压题目测试用例。"""
        self._require_teacher(requester_role)
        self._require_problem(params.problem_id)
        return self._test_case_storage.save_zip(
            params.problem_id, params.filename, params.content
        )

    def delete_test_cases(self, requester_role: str, problem_id: int) -> None:
        """删除题目的全部测试用例。"""
        self._require_teacher(requester_role)
        self._require_problem(problem_id)
        self._test_case_storage.delete_all(problem_id)

    def download_test_cases(self, requester_role: str, problem_id: int) -> bytes:
        """获取题目测试用例 ZIP 文件内容。"""
        self._require_teacher(requester_role)
        self._require_problem(problem_id)
        return self._test_case_storage.build_archive(problem_id)

    def _require_problem(self, problem_id: int):
        problem = self._problem_repository.get_by_id(problem_id)
        if problem is None:
            raise ResourceNotFoundError("题目不存在")
        return problem

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

    @staticmethod
    def _to_list_item(problem) -> ProblemListItem:
        return ProblemListItem(
            id=problem.id,
            title=problem.title,
            problem_type=problem.type,
            language=problem.language,
            time_limit=problem.time_limit,
            memory_limit=problem.memory_limit,
        )

    @staticmethod
    def _to_detail(problem) -> ProblemDetail:
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

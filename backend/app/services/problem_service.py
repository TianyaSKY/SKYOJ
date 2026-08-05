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
from app.mappers import from_problem_orm
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
        return from_problem_orm(problem, with_content=True)

    def list_problems(
        self,
        requester_role: str,
        page: int | None = None,
        page_size: int | None = None,
    ) -> list[ProblemListItem] | PaginatedProblems:
        """查询题目列表，并在指定页码时返回分页结果。

        教师可见全部题目；其他角色仅可见已上传测试用例的题目。
        """
        if requester_role == "teacher":
            problems, total = self._problem_repository.list_all(
                page=page, page_size=page_size
            )
            items = [from_problem_orm(problem) for problem in problems]
            if page is None or page_size is None:
                return items

            return PaginatedProblems(
                total=total or 0,
                page=page,
                page_size=page_size,
                problems=items,
            )

        problems, _ = self._problem_repository.list_all()
        visible = [
            problem
            for problem in problems
            if self._test_case_storage.has_test_cases(problem.id)
        ]
        if page is None or page_size is None:
            return [from_problem_orm(problem) for problem in visible]

        start = (page - 1) * page_size
        paged = visible[start : start + page_size]
        return PaginatedProblems(
            total=len(visible),
            page=page,
            page_size=page_size,
            problems=[from_problem_orm(problem) for problem in paged],
        )

    def get_problem(self, problem_id: int) -> ProblemDetail:
        """获取题目详情。"""
        return from_problem_orm(self._require_problem(problem_id), with_content=True)

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

        return from_problem_orm(self._problem_repository.update(problem), with_content=True)

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

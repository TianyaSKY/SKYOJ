"""problem 业务参数、结果与服务。"""

from __future__ import annotations

from app.core.errors import PermissionDeniedError, ResourceNotFoundError
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CreateProblemParams:
    """创建题目参数。"""

    title: str
    content: str
    language: str
    problem_type: str
    time_limit: int = 1000
    memory_limit: int = 128
    template_code: str = ""


@dataclass(frozen=True)
class UpdateProblemParams:
    """更新题目参数。"""

    title: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    problem_type: Optional[str] = None
    time_limit: Optional[int] = None
    memory_limit: Optional[int] = None
    template_code: Optional[str] = None


@dataclass(frozen=True)
class UploadTestCasesParams:
    """上传题目测试用例的业务参数。"""

    problem_id: int
    filename: str
    content: bytes


@dataclass(frozen=True)
class TestCaseItem:
    """单个测试点的输入输出文件状态。"""

    name: str
    input_file: Optional[str]
    output_file: Optional[str]
    input_size: Optional[int]
    output_size: Optional[int]
    status: str


@dataclass(frozen=True)
class TestCaseSummary:
    """题目测试点的整体状态摘要。"""

    status: str
    total_count: int
    valid_count: int
    invalid_count: int
    file_count: int
    total_size: int
    ignored_files: list[str]
    cases: list[TestCaseItem]


@dataclass(frozen=True)
class ProblemListItem:
    """题目列表项。"""

    id: int
    title: str
    problem_type: str
    language: str
    time_limit: int
    memory_limit: int
    test_case_status: str = "unknown"
    test_case_count: int = 0
    test_case_valid_count: int = 0


@dataclass(frozen=True)
class ProblemDetail:
    """题目详情。"""

    id: int
    title: str
    content: str
    problem_type: str
    language: str
    time_limit: int
    memory_limit: int
    template_code: str
    test_case_path: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class PaginatedProblems:
    """分页题目列表。"""

    total: int
    page: int
    page_size: int
    problems: list[ProblemListItem]


@dataclass
class ProblemRecord:
    """Problem 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    title: str
    content: str
    type: str
    language: str
    time_limit: int | None
    memory_limit: int | None
    test_case_path: str | None
    template_code: str | None
    created_at: datetime | None


from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.persistence.community import ProblemCommunityRepository
from app.persistence.problem import ProblemRepository, to_problem_result
from app.utils.problem_cache import (
    get_detail_cache,
    invalidate_detail_cache,
    set_detail_cache,
)


class ProblemService:
    """编排题目的创建、查询、更新和删除业务。"""

    def __init__(
        self,
        problem_repository: ProblemRepository,
        test_case_storage: ProblemTestCaseStorageClient | None = None,
        community_repository: ProblemCommunityRepository | None = None,
    ) -> None:
        self._problem_repository = problem_repository
        self._community_repository = community_repository
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
        self._problem_repository.unit_of_work.commit()
        detail = to_problem_result(problem, with_content=True)
        # 新建题目的详情立即可缓存（首次读取必然命中）。
        set_detail_cache(detail.id, self._detail_to_dict(detail))
        return detail

    def list_problems(
        self,
        requester_role: str,
        page: int | None = None,
        page_size: int | None = None,
        tag_id: int | None = None,
    ) -> list[ProblemListItem] | PaginatedProblems:
        """查询题目列表，并在指定页码时返回分页结果。

        教师可见全部题目；其他角色仅可见已上传测试用例的题目。
        支持按 tag_id 过滤（仅返回关联该标签且 approved=True 的题目）。
        """
        allowed_ids: set[int] | None = None
        if tag_id is not None:
            if self._community_repository is None:
                raise RuntimeError("题目标签仓储未注入")
            ids = self._community_repository.list_problem_ids_by_tag(tag_id)
            if not ids:
                if page is not None and page_size is not None:
                    return PaginatedProblems(
                        total=0, page=page, page_size=page_size, problems=[]
                    )
                return []
            allowed_ids = set(ids)

        if requester_role == "teacher":
            problems, total = self._problem_repository.list_all(
                page=page, page_size=page_size
            )
            items = [
                self._with_test_case_status(to_problem_result(problem))
                for problem in problems
            ]
            if allowed_ids is not None:
                items = [p for p in items if p.id in allowed_ids]
                total = len(items)
            if page is None or page_size is None:
                return items
            return PaginatedProblems(
                total=total or 0, page=page, page_size=page_size, problems=items
            )

        problems, _ = self._problem_repository.list_all()
        visible = [
            problem
            for problem in problems
            if self._test_case_storage.has_test_cases(problem.id)
        ]
        if allowed_ids is not None:
            visible = [p for p in visible if p.id in allowed_ids]
        if page is None or page_size is None:
            return [to_problem_result(problem) for problem in visible]

        start = (page - 1) * page_size
        paged = visible[start : start + page_size]
        return PaginatedProblems(
            total=len(visible),
            page=page,
            page_size=page_size,
            problems=[to_problem_result(problem) for problem in paged],
        )

    def get_problem(self, problem_id: int) -> ProblemDetail:
        """获取题目详情：先查 Redis 缓存，未命中回源并回填。"""
        cached = get_detail_cache(problem_id)
        if cached is not None:
            return self._detail_from_dict(cached)
        problem = self._require_problem(problem_id)
        self._problem_repository.unit_of_work.commit()
        detail = to_problem_result(problem, with_content=True)
        set_detail_cache(detail.id, self._detail_to_dict(detail))
        return detail

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

        updated = to_problem_result(
            self._problem_repository.update(problem), with_content=True
        )
        self._problem_repository.unit_of_work.commit()
        # 写后失效：避免下次读取到陈旧内容。
        invalidate_detail_cache(problem_id)
        return updated

    def delete_problem(self, requester_role: str, problem_id: int) -> None:
        """删除题目记录。"""
        self._require_teacher(requester_role)
        problem = self._require_problem(problem_id)
        self._test_case_storage.delete_problem_directory(problem_id)
        self._problem_repository.delete(problem)
        self._problem_repository.unit_of_work.commit()
        invalidate_detail_cache(problem_id)

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

    def get_test_case_summary(
        self, requester_role: str, problem_id: int
    ) -> TestCaseSummary:
        """读取题目的测试点状态，仅供教师管理页面使用。"""
        self._require_teacher(requester_role)
        self._require_problem(problem_id)
        return self._test_case_storage.summarize(problem_id)

    def _with_test_case_status(self, item: ProblemListItem) -> ProblemListItem:
        summary = self._test_case_storage.summarize(item.id)
        return replace(
            item,
            test_case_status=summary.status,
            test_case_count=summary.total_count,
            test_case_valid_count=summary.valid_count,
        )

    def _require_problem(self, problem_id: int) -> ProblemRecord:
        problem = self._problem_repository.get_by_id(problem_id)
        if problem is None:
            raise ResourceNotFoundError("题目不存在")
        return problem

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

    @staticmethod
    def _detail_to_dict(detail: ProblemDetail) -> dict:
        """ProblemDetail → JSON 可序列化的 dict。"""
        return {
            "id": detail.id,
            "title": detail.title,
            "content": detail.content,
            "problem_type": detail.problem_type,
            "language": detail.language,
            "time_limit": detail.time_limit,
            "memory_limit": detail.memory_limit,
            "template_code": detail.template_code,
            "test_case_path": detail.test_case_path,
            "created_at": detail.created_at.isoformat() if detail.created_at else None,
        }

    @staticmethod
    def _detail_from_dict(payload: dict) -> ProblemDetail:
        """缓存 dict → ProblemDetail。"""
        from datetime import datetime

        created_at_raw = payload.get("created_at")
        created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else None
        return ProblemDetail(
            id=int(payload["id"]),
            title=payload["title"],
            content=payload["content"],
            problem_type=payload["problem_type"],
            language=payload["language"],
            time_limit=int(payload["time_limit"]),
            memory_limit=int(payload["memory_limit"]),
            template_code=payload.get("template_code", "") or "",
            test_case_path=payload.get("test_case_path"),
            created_at=created_at,
        )

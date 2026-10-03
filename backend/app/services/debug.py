"""debug 业务参数、结果与服务。"""

from __future__ import annotations

from app.core.errors import PermissionDeniedError, ResourceNotFoundError
from app.core.time import utcnow
from dataclasses import dataclass
from datetime import datetime
from loguru import logger
from typing import Optional, Protocol


@dataclass(frozen=True)
class CreateDebugRunParams:
    """创建调试运行的业务参数。"""

    user_id: int
    problem_id: int
    language: str
    code: str
    exam_id: Optional[int] = None


@dataclass(frozen=True)
class DebugRunResult:
    """创建调试运行后的同步结果。"""

    debug_run_id: int
    status: str
    exam_id: Optional[int] = None


@dataclass(frozen=True)
class DebugRunDetail:
    """调试运行详情。"""

    id: int
    status: str
    language: str
    case_name: Optional[str]
    input: Optional[str]
    expected_output: Optional[str]
    actual_output: Optional[str]
    error_output: Optional[str]
    time_used_ms: Optional[int]
    memory_used_kb: Optional[int]
    created_at: Optional[datetime]
    finished_at: Optional[datetime]
    problem_id: int
    user_id: int
    exam_id: Optional[int]


class DebugCaseRunner(Protocol):
    def __call__(
        self, *, user_code: str, problem_id: int, language: str
    ) -> SingleCaseResult: ...


_STATUS_MAP = {
    "passed": "Accepted",
    "wrong_answer": "Wrong Answer",
    "tle": "Time Limit Exceeded",
    "runtime_error": "Runtime Error",
    "compile_error": "Compile Error",
    "system_error": "System Error",
}


from app.clients.submission_storage_client import SubmissionStorageClient
from app.persistence.submission import DebugRunRepository, from_debug_run_orm
from app.services.acm import SingleCaseResult
from app.services.async_job import AsyncJobService


class DebugService:
    """ACM 调试运行编排：创建运行、异步判题并落库、查询运行结果。"""

    def __init__(
        self,
        debug_run_repository: DebugRunRepository,
        job_service: AsyncJobService | None,
        storage_client: SubmissionStorageClient | None = None,
        case_runner: DebugCaseRunner | None = None,
    ) -> None:
        self._repo = debug_run_repository
        self._job_service = job_service
        self._storage_client = storage_client
        self._case_runner = case_runner

    def create(
        self, params: CreateDebugRunParams, *, requester_role: str
    ) -> DebugRunResult:
        """创建一条调试记录并投递异步任务；在业务层校验角色和题目类型。"""
        if requester_role != "student":
            raise PermissionDeniedError("Only student accounts can run debug.")
        if self._job_service is None:
            raise RuntimeError("调试任务服务未注入")
        problem = self._repo.get_problem(params.problem_id)
        if problem is None:
            raise ResourceNotFoundError("题目不存在")
        problem_type = (problem.type or "acm").lower()
        if problem_type != "acm":
            raise ResourceNotFoundError("仅 ACM 类型题目支持调试运行")

        exam_id = self._resolve_exam_id(params.exam_id)
        code = params.code
        if self._storage_client is not None and getattr(
            params, "is_file_upload", False
        ):
            if (
                not getattr(params, "filename", None)
                or getattr(params, "file_content", None) is None
            ):
                raise ValueError("提交附件信息不完整")
            code = self._storage_client.save(
                params.user_id, params.problem_id, params.filename, params.file_content
            )

        row = self._repo.create(
            user_id=params.user_id,
            problem_id=params.problem_id,
            exam_id=exam_id,
            language=params.language,
            code=code,
        )
        self._repo.unit_of_work.commit()
        self._job_service.enqueue_debug_submission(row.id)
        return DebugRunResult(debug_run_id=row.id, status="Pending", exam_id=exam_id)

    def _resolve_exam_id(self, exam_id: int | None) -> int | None:
        if exam_id is None or exam_id == -1:
            return None
        exam = self._repo.get_active_exam(exam_id, utcnow())
        return exam.id if exam is not None else None

    def get_debug_run(
        self, debug_run_id: int, requester_id: int, requester_role: str
    ) -> DebugRunDetail:
        """查询调试记录；学生只能查看自己的记录。"""
        row = self._repo.get_by_id(debug_run_id)
        if row is None:
            raise ResourceNotFoundError("调试记录不存在")
        if requester_role == "student" and row.user_id != requester_id:
            raise PermissionDeniedError("无权查看该调试记录")
        return from_debug_run_orm(row)

    def run_debug(self, debug_run_id: int) -> None:
        """Celery worker 调用：在 Judge 容器中执行单个测试点并写回结果。

        `job_service` 参数仅在 create() 投递任务时使用；run_debug 内部不投递任务，
        因此 worker 入口传入 None 也是安全的。
        """
        row = self._repo.get_by_id(debug_run_id)
        if row is None:
            logger.warning("调试记录不存在，跳过 debug_run_id={}", debug_run_id)
            return
        if self._case_runner is None:
            raise RuntimeError("调试运行器未注入")
        try:
            result = self._case_runner(
                user_code=row.code_content or "",
                problem_id=row.problem_id,
                language=row.language or "python",
            )
            status = _STATUS_MAP.get(result.status, "System Error")
            self._repo.finish(
                debug_run_id,
                status=status,
                case_name=result.case_name or None,
                input_data=result.input_data or "",
                expected_output=result.expected_output or "",
                actual_output=result.actual_output or "",
                error_output=result.error_output or "",
            )
            self._repo.unit_of_work.commit()
        except Exception as exc:
            self._repo.unit_of_work.rollback()
            logger.exception("调试运行业务执行异常 debug_run_id={}", debug_run_id)
            self._repo.finish(
                debug_run_id,
                status="System Error",
                error_output=str(exc),
            )
            self._repo.unit_of_work.commit()

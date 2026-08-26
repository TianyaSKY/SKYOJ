"""调试运行业务服务。"""

from datetime import datetime

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.debug_run import (
    CreateDebugRunParams,
    DebugRunDetail,
    DebugRunResult,
)
from app.domain.errors import PermissionDeniedError, ResourceNotFoundError
from app.mappers import from_debug_run_orm
from app.repositories.debug_run_repository import DebugRunRepository
from app.services.acm import run_acm_single_case


_STATUS_MAP = {
    "passed": "Accepted",
    "wrong_answer": "Wrong Answer",
    "tle": "Time Limit Exceeded",
    "runtime_error": "Runtime Error",
    "compile_error": "Compile Error",
    "system_error": "System Error",
}


class DebugService:
    """ACM 调试运行编排：创建运行、异步判题并落库、查询运行结果。"""

    def __init__(
        self,
        debug_run_repository: DebugRunRepository,
        job_service,
        storage_client=None,
    ) -> None:
        self._repo = debug_run_repository
        self._job_service = job_service
        self._storage_client = storage_client

    def create(self, params: CreateDebugRunParams) -> DebugRunResult:
        """创建一条调试记录并投递异步任务；非 ACM 题目在 API 层拦截。"""
        from app.repositories.submission_repository import SubmissionRepository

        db = self._repo._db
        problem = SubmissionRepository(db).get_problem(params.problem_id)
        if problem is None:
            raise ResourceNotFoundError("题目不存在")
        problem_type = (problem.type or "acm").lower()
        if problem_type != "acm":
            raise ResourceNotFoundError("仅 ACM 类型题目支持调试运行")

        exam_id = self._resolve_exam_id(params.exam_id)
        code = params.code
        if self._storage_client is not None and getattr(params, "is_file_upload", False):
            if not getattr(params, "filename", None) or getattr(params, "file_content", None) is None:
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
        self._job_service.enqueue_debug_submission(row.id)
        return DebugRunResult(debug_run_id=row.id, status="Pending", exam_id=exam_id)

    def _resolve_exam_id(self, exam_id: int | None) -> int | None:
        from app.repositories.submission_repository import SubmissionRepository

        if exam_id is None or exam_id == -1:
            return None
        exam = SubmissionRepository(self._repo._db).get_active_exam(
            exam_id, datetime.now()
        )
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
        db: Session = self._repo._db
        try:
            result = run_acm_single_case(
                user_code=row.code_content or "",
                problem_id=row.problem_id,
                language=row.language or "python",
                db=db,
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
        except Exception as exc:
            logger.exception("调试运行业务执行异常 debug_run_id={}", debug_run_id)
            self._repo.finish(
                debug_run_id,
                status="System Error",
                error_output=str(exc),
            )


__all__ = ["DebugService"]

"""剽窃检测 API 的业务编排服务。"""

from typing import TYPE_CHECKING

from app.domain.errors import PermissionDeniedError, ResourceNotFoundError
from app.domain.plagiarism import BatchCheckParams, PaginatedPlagiarismLogs, PlagiarismLogDetail, PlagiarismLogItem
from app.repositories.plagiarism_repository import PlagiarismRepository

if TYPE_CHECKING:
    from app.services.plagiarism_service import PlagiarismService


class PlagiarismFacadeService:
    """处理剽窃检测的权限、日志查询和异步任务提交。"""

    def __init__(self, repository: PlagiarismRepository, worker: "PlagiarismService", enabled: bool) -> None:
        self._repository = repository
        self._worker = worker
        self._enabled = enabled

    def list_logs(self, requester_role: str, problem_id: int | None, exam_id: int | None, min_score: float, page: int, page_size: int) -> PaginatedPlagiarismLogs:
        self._require_teacher(requester_role)
        logs, total, pages = self._repository.list(problem_id, exam_id, min_score, page, page_size)
        return PaginatedPlagiarismLogs(total, page, page_size, [self._to_item(log) for log in logs])

    def get_log(self, submission_id: int, requester_id: int, requester_role: str) -> PlagiarismLogDetail:
        log = self._repository.get_by_submission_id(submission_id)
        if log is None:
            raise ResourceNotFoundError("剽窃检测日志不存在")
        if requester_role == "student" and log.submission.user_id != requester_id:
            raise PermissionDeniedError("无权查看该剽窃检测日志")
        item = self._to_item(log)
        return PlagiarismLogDetail(**item.__dict__, code_content=log.submission.code_content, target_code=log.target_submission.code_content if log.target_submission else None)

    def start_batch_check(self, requester_role: str, params: BatchCheckParams) -> None:
        self._require_teacher(requester_role)
        if not self._enabled:
            raise PermissionDeniedError("剽窃检测服务当前未启用")
        self._worker.start_check_task(params.submission_ids)

    def delete_log(self, requester_role: str, log_id: int) -> None:
        self._require_teacher(requester_role)
        log = self._repository.get_by_id(log_id)
        if log is None:
            raise ResourceNotFoundError("剽窃检测日志不存在")
        self._repository.delete(log)

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

    @staticmethod
    def _to_item(log) -> PlagiarismLogItem:
        submission = log.submission
        return PlagiarismLogItem(log.id, log.submission_id, log.target_submission_id, round(log.similarity_score, 2), log.created_at, submission.user.username if submission and submission.user else None, submission.problem_id if submission else None, submission.problem.title if submission and submission.problem else None, submission.exam_id if submission else None, submission.user_id if submission else None)

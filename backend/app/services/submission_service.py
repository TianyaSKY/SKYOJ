"""提交与判题业务服务。"""

from datetime import datetime

from app.domain.errors import PermissionDeniedError, ResourceNotFoundError
from app.domain.submission import (
    PaginatedSubmissions,
    SubmissionDetail,
    SubmissionListItem,
    SubmissionQuery,
    SubmitParams,
    SubmitResult,
)
from app.repositories.submission_repository import SubmissionRepository
from app.clients.submission_storage_client import SubmissionStorageClient
from app.services.async_job_service import AsyncJobService


class SubmissionService:
    """处理提交创建、考试关联和判题任务投递。"""

    def __init__(
        self,
        submission_repository: SubmissionRepository,
        job_service: AsyncJobService,
        storage_client: SubmissionStorageClient | None = None,
    ) -> None:
        self._submission_repository = submission_repository
        self._job_service = job_service
        self._storage_client = storage_client or SubmissionStorageClient()

    def submit(self, params: SubmitParams) -> SubmitResult:
        """保存提交并异步启动判题。"""
        problem = self._submission_repository.get_problem(params.problem_id)
        if problem is None:
            raise ResourceNotFoundError("题目不存在")

        exam_id = self._resolve_exam_id(params.exam_id)
        code = params.code
        if params.is_file_upload:
            if not params.filename or params.file_content is None:
                raise ValueError("提交附件信息不完整")
            code = self._storage_client.save(
                params.user_id, params.problem_id, params.filename, params.file_content
            )
        submission = self._submission_repository.create(
            params.user_id, params.problem_id, exam_id, params.language, code
        )
        self._job_service.enqueue_judge_submission(submission.id)
        return SubmitResult(submission_id=submission.id, status="Pending", exam_id=exam_id)

    def _resolve_exam_id(self, exam_id: int | None) -> int | None:
        if exam_id is None or exam_id == -1:
            return None
        exam = self._submission_repository.get_active_exam(exam_id, datetime.now())
        return exam.id if exam is not None else None

    def list_submissions(self, params: SubmissionQuery) -> PaginatedSubmissions:
        """按访问者权限和筛选条件分页查询提交记录。"""
        user_id = params.requester_id if params.requester_role == "student" else params.user_id
        submissions, total, pages = self._submission_repository.list(
            params.problem_id, user_id, params.exam_id, params.status,
            params.username, params.page, params.page_size,
        )
        return PaginatedSubmissions(
            total=total, pages=pages, current_page=params.page,
            submissions=[self._to_list_item(item) for item in submissions],
        )

    def get_submission(
        self, submission_id: int, requester_id: int, requester_role: str
    ) -> SubmissionDetail:
        """查询单条提交，并校验学生只能查看自己的记录。"""
        submission = self._submission_repository.get_by_id(submission_id)
        if submission is None:
            raise ResourceNotFoundError("提交记录不存在")
        if requester_role == "student" and submission.user_id != requester_id:
            raise PermissionDeniedError("无权查看该提交记录")
        return SubmissionDetail(
            id=submission.id, status=submission.status, score=submission.score,
            log=submission.output_log, code=submission.code_content,
            language=submission.language, exam_id=submission.exam_id,
            created_at=submission.created_at,
        )

    @staticmethod
    def _to_list_item(submission) -> SubmissionListItem:
        return SubmissionListItem(
            id=submission.id, user_id=submission.user_id,
            username=submission.user.username, problem_id=submission.problem_id,
            exam_id=submission.exam_id, status=submission.status,
            score=submission.score, language=submission.language,
            created_at=submission.created_at,
        )

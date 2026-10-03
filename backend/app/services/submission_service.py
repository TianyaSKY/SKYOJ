"""提交与判题业务服务。"""

from datetime import timedelta

from app.clients.submission_storage_client import SubmissionStorageClient
from app.domain.analytics import PlatformAnalytics, ProblemDifficulty, ProblemPassRate
from app.domain.errors import (
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.domain.submission import (
    PaginatedSubmissions,
    SubmissionDetail,
    SubmissionQuery,
    SubmitParams,
    SubmitResult,
)
from app.mappers import from_submission_detail_orm, from_submission_orm
from app.repositories.submission_repository import SubmissionRepository
from app.services.async_job_service import AsyncJobService
from app.utils.time import utcnow


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

    def submit(self, params: SubmitParams, *, requester_role: str) -> SubmitResult:
        """保存提交并异步启动判题。"""
        if requester_role != "student":
            raise PermissionDeniedError("Only student accounts can submit solutions.")
        problem = self._submission_repository.get_problem(params.problem_id)
        if problem is None:
            raise ResourceNotFoundError("题目不存在")

        exam_id = self._resolve_exam_id(params.exam_id, params.session_exam_id)
        if (
            exam_id is not None
            and self._submission_repository.get_exam_problem(exam_id, params.problem_id)
            is None
        ):
            raise PermissionDeniedError("该题目不属于当前考试")
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
        self._submission_repository.unit_of_work.commit()
        self._job_service.enqueue_judge_submission(submission.id)
        return SubmitResult(
            submission_id=submission.id, status="Pending", exam_id=exam_id
        )

    def _resolve_exam_id(self, exam_id: int | None, session_exam_id: int) -> int | None:
        if session_exam_id != -1:
            if exam_id not in (None, -1, session_exam_id):
                raise PermissionDeniedError("未进入该考试，无法提交")
            exam_id = session_exam_id
        elif exam_id is None or exam_id == -1:
            return None
        else:
            raise PermissionDeniedError("未进入该考试，无法提交")

        exam = self._submission_repository.get_active_exam(exam_id, utcnow())
        if exam is None:
            raise InvalidStateError("考试未在进行中")
        return exam.id

    def list_submissions(self, params: SubmissionQuery) -> PaginatedSubmissions:
        """按访问者权限和筛选条件分页查询提交记录。"""
        user_id = (
            params.requester_id
            if params.requester_role == "student"
            else params.user_id
        )
        submissions, total, pages = self._submission_repository.list_all(
            params.problem_id,
            user_id,
            params.exam_id,
            params.status,
            params.username,
            params.page,
            params.page_size,
        )
        return PaginatedSubmissions(
            total=total,
            pages=pages,
            current_page=params.page,
            submissions=[from_submission_orm(item) for item in submissions],
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
        return from_submission_detail_orm(submission)

    def get_platform_analytics(self, requester_role: str) -> PlatformAnalytics:
        """聚合平台统计，仅教师可以访问。"""
        if requester_role != "teacher":
            raise PermissionDeniedError("仅教师可访问")
        import math

        total, accepted, problems = self._submission_repository.get_global_counts()
        counts = self._submission_repository.get_problem_submission_counts()
        pass_rates = [
            ProblemPassRate(
                row.problem_id, row.title, row.accepted / row.total, row.total
            )
            for row in counts
        ]
        difficulty = [
            ProblemDifficulty(
                row.problem_id,
                row.title,
                min(
                    math.log(row.total + 1) * (1 - row.accepted / row.total) * 100,
                    100.0,
                ),
                row.total,
            )
            for row in counts
        ]
        difficulty.sort(key=lambda row: row.difficulty, reverse=True)
        return PlatformAnalytics(
            total,
            accepted,
            accepted / total if total else 0.0,
            problems,
            pass_rates,
            difficulty[:20],
            self._submission_repository.get_daily_submission_counts(
                utcnow() - timedelta(days=30)
            ),
        )

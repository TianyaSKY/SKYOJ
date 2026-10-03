"""submission 业务参数、结果与服务。"""

from __future__ import annotations

from app.core.errors import (
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.core.json import JsonValue
from app.core.time import utcnow
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from app.services.user import UserRecord
    from app.services.problem import ProblemRecord


@dataclass(frozen=True)
class SubmitParams:
    """提交代码参数。"""

    user_id: int
    problem_id: int
    code: str
    language: str
    exam_id: Optional[int] = None
    session_exam_id: int = -1
    is_file_upload: bool = False
    filename: Optional[str] = None
    file_content: Optional[bytes] = None


@dataclass(frozen=True)
class SubmissionListItem:
    """提交列表项。"""

    id: int
    user_id: int
    username: str
    problem_id: int
    exam_id: Optional[int]
    status: str
    score: float
    language: str
    created_at: Optional[datetime]


@dataclass(frozen=True)
class SubmissionDetail:
    """提交详情。"""

    id: int
    status: str
    score: float
    log: Optional[str]
    code: Optional[str]
    language: str
    exam_id: Optional[int]
    created_at: Optional[datetime]
    case_results: list["CaseResult"] = field(default_factory=list)


@dataclass(frozen=True)
class PaginatedSubmissions:
    """分页提交列表。"""

    total: int
    pages: int
    current_page: int
    submissions: list[SubmissionListItem]


@dataclass(frozen=True)
class SubmissionQuery:
    """查询提交列表的业务参数。"""

    requester_id: int
    requester_role: str
    problem_id: Optional[int] = None
    user_id: Optional[int] = None
    exam_id: Optional[int] = None
    status: Optional[str] = None
    username: Optional[str] = None
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class SubmitResult:
    """提交代码后的结果。"""

    submission_id: int
    status: str
    exam_id: Optional[int] = None


# 单点判题结果：与 ACM 容器内 SingleCaseResult 字段对齐，但只保留对外需要的部分。
# - case_name: 来自测试数据文件名（如 "1"、"2"）
# - status: passed / wrong_answer / tle / runtime_error / compile_error / system_error
# - time_used_ms: 判题耗时（仅 passed/wrong_answer/tle 时记录；其他场景可空）
# - memory_used_kb: 峰值内存（占位，ACM judge 当前未取真实值，可空）
# - input_data / expected_output / actual_output / error_output:
#   仅当 verbose 模式（单点调试）写入，提交整体跑时不带这四个字段以减小行体积。
CaseStatus = str


@dataclass(frozen=True)
class CaseResult:
    """单测试点结果（聚合写入 Submission.case_results JSON 列）。"""

    case_name: str
    status: CaseStatus
    time_used_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    error_output: Optional[str] = None


@dataclass(frozen=True)
class ProblemSubmissionCounts:
    problem_id: int
    title: str
    total: int
    accepted: int


@dataclass(frozen=True)
class ProblemPassRate:
    problem_id: int
    title: str
    pass_rate: float
    total: int


@dataclass(frozen=True)
class ProblemDifficulty:
    problem_id: int
    title: str
    difficulty: float
    total: int


@dataclass(frozen=True)
class DailySubmissionCount:
    date: str
    count: int


@dataclass(frozen=True)
class PlatformAnalytics:
    total_submissions: int
    total_accepted: int
    global_pass_rate: float
    total_problems: int
    problem_pass_rates: list[ProblemPassRate]
    problem_difficulty: list[ProblemDifficulty]
    daily_submissions: list[DailySubmissionCount]


@dataclass
class SubmissionRecord:
    """Submission 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    user_id: int
    problem_id: int
    exam_id: int | None
    code_path: str | None
    code_content: str | None
    language: str | None
    status: str | None
    score: float | None
    output_log: str | None
    case_results: list[dict[str, JsonValue]] | None
    created_at: datetime | None
    user: UserRecord | None
    problem: ProblemRecord | None


from app.clients.submission_storage_client import SubmissionStorageClient
from app.persistence.submission import (
    SubmissionRepository,
    to_submission_detail,
    to_submission_list_item,
)
from app.services.async_job import AsyncJobService


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
            submissions=[to_submission_list_item(item) for item in submissions],
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
        return to_submission_detail(submission)

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

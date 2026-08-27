"""提交与判题业务服务。"""

from datetime import datetime, timedelta

from app.domain.errors import InvalidStateError, PermissionDeniedError, ResourceNotFoundError
from app.utils.time import utcnow
from app.domain.submission import (
    PaginatedSubmissions,
    SubmissionDetail,
    SubmissionQuery,
    SubmitParams,
    SubmitResult,
)
from app.mappers import from_submission_detail_orm, from_submission_orm
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

        exam_id = self._resolve_exam_id(params.exam_id, params.session_exam_id)
        if exam_id is not None and self._submission_repository.get_exam_problem(exam_id, params.problem_id) is None:
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
        self._job_service.enqueue_judge_submission(submission.id)
        return SubmitResult(submission_id=submission.id, status="Pending", exam_id=exam_id)

    def _resolve_exam_id(self, exam_id: int | None, session_exam_id: int) -> int | None:
        if exam_id is None or exam_id == -1:
            return None
        if session_exam_id != exam_id:
            raise PermissionDeniedError("未进入该考试，无法提交")
        exam = self._submission_repository.get_active_exam(exam_id, utcnow())
        if exam is None:
            raise InvalidStateError("考试未在进行中")
        return exam.id

    def list_submissions(self, params: SubmissionQuery) -> PaginatedSubmissions:
        """按访问者权限和筛选条件分页查询提交记录。"""
        user_id = params.requester_id if params.requester_role == "student" else params.user_id
        submissions, total, pages = self._submission_repository.list_all(
            params.problem_id, user_id, params.exam_id, params.status,
            params.username, params.page, params.page_size,
        )
        return PaginatedSubmissions(
            total=total, pages=pages, current_page=params.page,
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

    def get_platform_analytics(self) -> dict:
        """平台全局学情分析（教师用）。"""
        import math
        from collections import defaultdict

        from app.models.submission import Submission
        from app.models.problem import Problem

        db = self._submission_repository._db
        submissions = db.query(Submission).all()
        problems = db.query(Problem).all()
        total_submissions = len(submissions)
        total_accepted = sum(1 for s in submissions if s.status == "Accepted")
        global_pass_rate = total_accepted / total_submissions if total_submissions > 0 else 0.0

        # 每题通过率
        problem_submissions: dict[int, list[Submission]] = defaultdict(list)
        for s in submissions:
            problem_submissions[s.problem_id].append(s)

        problem_pass_rates = []
        for problem in problems:
            subs = problem_submissions.get(problem.id, [])
            if not subs:
                continue
            ac = sum(1 for s in subs if s.status == "Accepted")
            problem_pass_rates.append({
                "problem_id": problem.id,
                "title": problem.title,
                "pass_rate": ac / len(subs),
                "total": len(subs),
            })

        # 题目难度：log(提交数+1) × 错误率 × 100，值越大越难
        problem_difficulty = []
        for problem in problems:
            subs = problem_submissions.get(problem.id, [])
            if not subs:
                continue
            ac = sum(1 for s in subs if s.status == "Accepted")
            err_rate = 1 - ac / len(subs)
            difficulty = math.log(len(subs) + 1) * err_rate * 100
            problem_difficulty.append({
                "problem_id": problem.id,
                "title": problem.title,
                "difficulty": min(difficulty, 100.0),
                "total": len(subs),
            })
        problem_difficulty.sort(key=lambda x: x["difficulty"], reverse=True)

        # 每日提交（近 30 天）
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_subs = [s for s in submissions if s.created_at and s.created_at >= thirty_days_ago]
        daily_map: dict[str, int] = defaultdict(int)
        for s in recent_subs:
            date_str = s.created_at.strftime("%Y-%m-%d")
            daily_map[date_str] += 1
        daily_submissions = [
            {"date": date_str, "count": count}
            for date_str, count in sorted(daily_map.items())
        ]

        return {
            "total_submissions": total_submissions,
            "total_accepted": total_accepted,
            "global_pass_rate": global_pass_rate,
            "total_problems": len(problems),
            "problem_pass_rates": problem_pass_rates,
            "problem_difficulty": problem_difficulty[:20],
            "daily_submissions": daily_submissions,
        }

"""ORM → 领域 dataclass 的唯一映射层。

各 service 不再手写 _to_* 方法；跨实体字段（username、problem_title 等）依赖
调用方预取对应关系，映射器只做字段搬运，不触发查询。
"""

from app.domain.ai_draft import AiDraftDetail, AiDraftSummary
from app.domain.async_job import AsyncJobResult
from app.domain.dataset import DatasetDetail, DatasetListItem
from app.domain.exam import ExamDetail, ExamListItem, ExamProblemItem
from app.domain.problem import ProblemDetail, ProblemListItem
from app.domain.submission import SubmissionDetail, SubmissionListItem
from app.domain.user import UserProfile, UserSubmissionItem
from app.repositories.ai_draft_repository import AiDraftRepository


def from_problem_orm(problem, *, with_content: bool = False) -> ProblemListItem | ProblemDetail:
    """题目 ORM → 列表项或详情。"""
    if with_content:
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
    return ProblemListItem(
        id=problem.id,
        title=problem.title,
        problem_type=problem.type,
        language=problem.language,
        time_limit=problem.time_limit,
        memory_limit=problem.memory_limit,
    )


def from_submission_orm(submission) -> SubmissionListItem:
    """提交 ORM → 列表项（username 取 submission.user.username，调用方须预取）。"""
    return SubmissionListItem(
        id=submission.id,
        user_id=submission.user_id,
        username=submission.user.username,
        problem_id=submission.problem_id,
        exam_id=submission.exam_id,
        status=submission.status,
        score=submission.score,
        language=submission.language,
        created_at=submission.created_at,
    )


def from_submission_detail_orm(submission) -> SubmissionDetail:
    """提交 ORM → 详情（code=code_content，log=output_log）。"""
    return SubmissionDetail(
        id=submission.id,
        status=submission.status,
        score=submission.score,
        log=submission.output_log,
        code=submission.code_content,
        language=submission.language,
        exam_id=submission.exam_id,
        created_at=submission.created_at,
    )


def from_user_orm(user) -> UserProfile:
    """用户 ORM → 公开资料。"""
    return UserProfile(
        id=user.id,
        username=user.username,
        role=user.role,
        avatar=user.avatar,
    )


def from_user_submission_orm(submission) -> UserSubmissionItem:
    """提交 ORM → 用户提交项（problem_title 取 submission.problem.title，调用方须预取）。"""
    return UserSubmissionItem(
        id=submission.id,
        problem_id=submission.problem_id,
        problem_title=submission.problem.title if submission.problem else "Unknown",
        status=submission.status,
        score=submission.score,
        language=submission.language,
        created_at=submission.created_at,
        exam_id=submission.exam_id,
    )


def from_dataset_orm(dataset) -> DatasetListItem:
    """数据集 ORM → 列表项。"""
    return DatasetListItem(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description or "",
        uploader=dataset.uploader.username if dataset.uploader else "Unknown",
        file_size=dataset.file_size or "",
        created_at=dataset.created_at,
        status=getattr(dataset, "status", "ready") or "ready",
        download_url=f"/api/datasets/{dataset.id}/download",
    )


def from_dataset_detail_orm(dataset) -> DatasetDetail:
    """数据集 ORM → 详情。"""
    return DatasetDetail(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description or "",
        file_path=dataset.file_path,
        file_size=dataset.file_size or "",
        uploader_id=dataset.uploader_id,
        uploader=dataset.uploader.username if dataset.uploader else "Unknown",
        created_at=dataset.created_at,
        status=getattr(dataset, "status", "ready") or "ready",
    )


def from_exam_orm(exam, *, problem_count: int, submission_count: int) -> ExamListItem:
    """考试 ORM → 列表项（题目/提交数由调用方从批量方法取得）。"""
    return ExamListItem(
        id=exam.id,
        title=exam.title,
        description=exam.description or "",
        start_time=exam.start_time,
        end_time=exam.end_time,
        is_visible=exam.is_visible,
        created_by=exam.created_by,
        problem_count=problem_count,
        submission_count=submission_count,
        has_password=bool(exam.password),
    )


def from_exam_detail_orm(exam, problems) -> ExamDetail:
    """考试 ORM + 题目列表 → 详情（problems 需已预取 problem 关系）。"""
    return ExamDetail(
        id=exam.id,
        title=exam.title,
        description=exam.description or "",
        start_time=exam.start_time,
        end_time=exam.end_time,
        is_visible=exam.is_visible,
        created_by=exam.created_by,
        has_password=bool(exam.password),
        problems=[
            ExamProblemItem(item.problem_id, item.display_id, item.score, item.problem.title)
            for item in problems
        ],
    )


def from_ai_draft_orm(draft, *, detail: bool = False) -> AiDraftSummary | AiDraftDetail:
    """AI 草稿 ORM → 列表项或详情。"""
    if detail:
        return AiDraftDetail(
            id=draft.id,
            task_type=draft.task_type,
            status=draft.status,
            title=draft.title or "",
            problem_id=draft.problem_id,
            request_payload=AiDraftRepository.parse_json_field(draft.request_payload),
            result_payload=AiDraftRepository.parse_json_field(draft.result_payload),
            error_message=draft.error_message,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            consumed_at=draft.consumed_at,
        )
    return AiDraftSummary(
        id=draft.id,
        task_type=draft.task_type,
        status=draft.status,
        title=draft.title or "",
        problem_id=draft.problem_id,
        error_message=draft.error_message,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        consumed_at=draft.consumed_at,
    )


def from_async_job_orm(job) -> AsyncJobResult:
    """异步任务 ORM → 对外快照。"""
    return AsyncJobResult(
        id=job.id,
        task_name=job.task_name,
        queue=job.queue,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        lease_until=job.lease_until,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )

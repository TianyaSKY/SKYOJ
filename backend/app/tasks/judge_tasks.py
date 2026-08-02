"""Judge Worker 任务：提交判题和测试数据执行。"""

from typing import Any

from loguru import logger

from app.database import SessionLocal
from app.domain.ai_draft import TASK_TEST_DATA_EXECUTION
from app.domain.async_job import EXECUTE_TEST_DATA_TASK, JUDGE_SUBMISSION_TASK
from app.messaging.celery_app import celery_app
from app.repositories.ai_draft_repository import AiDraftRepository
from app.repositories.async_job_repository import AsyncJobRepository
from app.services.async_job_service import AsyncJobService
from app.services.judge_service import (
    judge_submission as run_submission_judge,
    save_non_acm_script,
)
from app.services.test_gen_service import run_test_generation


@celery_app.task(name=JUDGE_SUBMISSION_TASK, ignore_result=True)
def judge_submission(job_id: int) -> None:
    """执行一条提交的判题任务。"""
    db = SessionLocal()
    job_service = AsyncJobService.from_session(db)
    started = job_service.start_job(
        job_id,
        lease_seconds=job_service.lease_seconds(JUDGE_SUBMISSION_TASK),
    )
    if started is None:
        db.close()
        return

    try:
        job = AsyncJobRepository(db).get_by_id(job_id)
        if job is None:
            raise ValueError(f"异步任务不存在: {job_id}")
        payload = job_service.parse_payload(job.payload)
        submission_id = int(payload["submission_id"])
        run_submission_judge(submission_id, db=db)
        job_service.complete_job(job_id)
    except Exception as exc:
        logger.exception("判题任务执行失败 job_id={}", job_id)
        job_service.fail_job(job_id, str(exc))
    finally:
        db.close()


@celery_app.task(name=EXECUTE_TEST_DATA_TASK, ignore_result=True)
def execute_test_data(job_id: int) -> None:
    """在 Judge Worker 中执行生成测试数据的脚本。"""
    db = SessionLocal()
    job_service = AsyncJobService.from_session(db)
    started = job_service.start_job(
        job_id,
        lease_seconds=job_service.lease_seconds(EXECUTE_TEST_DATA_TASK),
    )
    if started is None:
        db.close()
        return

    draft_id: int | None = None
    draft_repository = AiDraftRepository(db)
    try:
        job = AsyncJobRepository(db).get_by_id(job_id)
        if job is None:
            raise ValueError(f"异步任务不存在: {job_id}")
        payload = job_service.parse_payload(job.payload)
        draft_id = int(payload["draft_id"])
        draft = draft_repository.get_by_id(draft_id)
        if draft is None:
            raise ValueError(f"AI 草稿不存在: {draft_id}")
        draft_repository.mark_running(draft_id)
        request = draft_repository.parse_json_field(draft.request_payload)
        result_payload = _run_test_data_execution(request)
        draft_repository.mark_success(
            draft_id,
            result_payload=result_payload,
            title=f"测例执行 · 题目 #{result_payload['problem_id']}",
        )
        job_service.complete_job(job_id)
    except _PermanentTestDataError as exc:
        logger.warning("测试数据任务失败且不再重试 job_id={} draft_id={}", job_id, draft_id)
        if draft_id is not None:
            draft_repository.mark_failed(draft_id, str(exc))
        job_service.fail_job(job_id, str(exc), retry=False)
    except Exception as exc:
        logger.exception("测试数据任务执行失败 job_id={} draft_id={}", job_id, draft_id)
        result = job_service.fail_job(job_id, str(exc))
        if draft_id is not None and result is not None and result.status == "failed":
            draft_repository.mark_failed(draft_id, str(exc))
    finally:
        db.close()


class _PermanentTestDataError(Exception):
    """脚本参数或题目状态错误，不应重复执行。"""


def _run_test_data_execution(
    request: dict[str, Any],
) -> dict[str, Any]:
    """执行 ACM 测试数据脚本或保存非 ACM 测试脚本。"""
    try:
        problem_id = int(request["problem_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _PermanentTestDataError("测试数据任务缺少有效 problem_id") from exc

    code = str(request.get("code") or "")
    problem_type = str(request.get("problem_type") or request.get("type") or "acm")
    language = str(request.get("language") or "python")
    if not code.strip():
        raise _PermanentTestDataError("执行代码为空")

    if problem_type != "acm":
        success, message = save_non_acm_script(problem_id, code, problem_type, language)
    else:
        success, message = run_test_generation(problem_id, code)
    if not success:
        raise RuntimeError(message)
    return {
        "message": message,
        "problem_id": problem_id,
        "problem_type": problem_type,
        "language": language,
        "task_type": TASK_TEST_DATA_EXECUTION,
    }


__all__ = ["execute_test_data", "judge_submission"]

"""Judge Worker 任务：提交判题和测试数据执行。"""

from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.domain.ai_draft import TASK_TEST_DATA_EXECUTION
from app.messaging.celery_app import celery_app
from app.messaging.task_names import EXECUTE_TEST_DATA_TASK, JUDGE_SUBMISSION_TASK
from app.repositories.ai_draft_repository import AiDraftRepository
from app.services.judge_service import (
    judge_submission as run_submission_judge,
    save_non_acm_script,
)
from app.services.test_gen_service import run_test_generation
from app.tasks.base import run_job


@celery_app.task(name=JUDGE_SUBMISSION_TASK, ignore_result=True)
def judge_submission(job_id: int) -> None:
    """执行一条提交的判题任务。"""
    run_job(
        job_id,
        task_name=JUDGE_SUBMISSION_TASK,
        handler=_handle_judge_submission,
    )


@celery_app.task(name=EXECUTE_TEST_DATA_TASK, ignore_result=True)
def execute_test_data(job_id: int) -> None:
    """在 Judge Worker 中执行生成测试数据的脚本。"""
    run_job(
        job_id,
        task_name=EXECUTE_TEST_DATA_TASK,
        handler=_handle_test_data_execution,
        on_failed=_mark_draft_failed,
        permanent_errors=(_PermanentTestDataError,),
    )


def _handle_judge_submission(db: Session, payload: dict[str, Any]) -> None:
    """执行提交判题。"""
    run_submission_judge(int(payload["submission_id"]), db)


def _handle_test_data_execution(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """执行 ACM 测试数据脚本或保存非 ACM 测试脚本，并更新草稿状态。"""
    draft_id = int(payload["draft_id"])
    draft = AiDraftRepository(db).get_by_id(draft_id)
    if draft is None:
        raise ValueError(f"AI 草稿不存在: {draft_id}")
    AiDraftRepository(db).mark_running(draft_id)
    request = AiDraftRepository.parse_json_field(draft.request_payload)
    result_payload = _run_test_data_execution(request)
    AiDraftRepository(db).mark_success(
        draft_id,
        result_payload=result_payload,
        title=f"测例执行 · 题目 #{result_payload['problem_id']}",
    )
    return result_payload


def _mark_draft_failed(payload: dict[str, Any], result) -> None:
    """任务失败后将草稿标记为失败。"""
    db = SessionLocal()
    try:
        AiDraftRepository(db).mark_failed(int(payload["draft_id"]), str(result))
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

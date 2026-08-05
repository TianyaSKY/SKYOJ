"""AI Worker 任务：出题和测试脚本生成。"""

from typing import Any

from sqlalchemy.orm import Session

from app.clients.llm_client import LlmClient
from app.database import SessionLocal
from app.messaging.celery_app import celery_app
from app.messaging.task_names import GENERATE_PROBLEM_TASK, GENERATE_TEST_SCRIPT_TASK
from app.repositories.ai_draft_repository import AiDraftRepository
from app.repositories.async_job_repository import AsyncJobRepository
from app.repositories.problem_repository import ProblemRepository
from app.services.ai_draft_service import AiDraftService
from app.services.async_job_service import AsyncJobService
from app.tasks.base import run_job


@celery_app.task(name=GENERATE_PROBLEM_TASK, ignore_result=True)
def generate_problem(job_id: int) -> None:
    """执行 AI 出题任务。"""
    run_job(
        job_id,
        task_name=GENERATE_PROBLEM_TASK,
        handler=_handle_generate_problem,
        on_failed=_mark_draft_failed,
    )


@celery_app.task(name=GENERATE_TEST_SCRIPT_TASK, ignore_result=True)
def generate_test_script(job_id: int) -> None:
    """执行 AI 测试脚本生成任务。"""
    run_job(
        job_id,
        task_name=GENERATE_TEST_SCRIPT_TASK,
        handler=_handle_generate_test_script,
        on_failed=_mark_draft_failed,
    )


def _build_service(db: Session) -> AiDraftService:
    """Worker 内构造 AI 草稿服务（与 api/deps.get_ai_draft_service 同构）。"""
    return AiDraftService(
        draft_repository=AiDraftRepository(db),
        problem_repository=ProblemRepository(db),
        job_service=AsyncJobService.from_session(db),
        llm_client=LlmClient(),
    )


def _handle_generate_problem(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """调用 LLM 生成题目并写入草稿箱。"""
    return _build_service(db).generate_problem(int(payload["draft_id"]), db)


def _handle_generate_test_script(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """调用 LLM 生成 ACM/OOP/Kaggle 测试脚本。"""
    return _build_service(db).generate_test_script(int(payload["draft_id"]), db)


def _mark_draft_failed(payload: dict[str, Any], result) -> None:
    """任务失败后将草稿标记为失败。"""
    db = SessionLocal()
    try:
        AiDraftRepository(db).mark_failed(int(payload["draft_id"]), str(result))
    finally:
        db.close()


__all__ = ["generate_problem", "generate_test_script"]

"""FastAPI 依赖注入。"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.clients.llm_client import LlmClient
from app.database import get_db
from app.repositories.ai_draft_repository import AiDraftRepository
from app.repositories.problem_repository import ProblemRepository
from app.services.ai_draft_service import AiDraftService
from app.tasks.queue import get_task_queue


def get_ai_draft_service(db: Session = Depends(get_db)) -> AiDraftService:
    """构造 AI 草稿服务。"""
    return AiDraftService(
        draft_repository=AiDraftRepository(db),
        problem_repository=ProblemRepository(db),
        task_queue=get_task_queue(),
        llm_client=LlmClient(),
    )

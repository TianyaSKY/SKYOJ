"""查重异步任务。"""

from typing import Any

from sqlalchemy.orm import Session

from app.clients.jplag_client import JPlagClient
from app.messaging.celery_app import celery_app
from app.messaging.task_names import SCAN_PLAGIARISM_TASK
from app.persistence.submission import PlagiarismRepository, SubmissionRepository
from app.persistence.unit_of_work import UnitOfWork
from app.services.plagiarism import PlagiarismService
from app.tasks.base import run_job


@celery_app.task(name=SCAN_PLAGIARISM_TASK, ignore_result=True)
def scan_plagiarism(job_id: int) -> None:
    """执行指定题目的批量代码查重。"""
    run_job(
        job_id,
        task_name=SCAN_PLAGIARISM_TASK,
        handler=_handle_scan,
    )


def _handle_scan(db: Session, payload: dict[str, Any]) -> None:
    uow = UnitOfWork(db)
    problem_id: int = payload["problem_id"]
    min_similarity: float = payload.get("min_similarity", 0.3)
    service = PlagiarismService(
        plagiarism_repo=PlagiarismRepository(db),
        submission_repo=SubmissionRepository(db),
        jplag_client=JPlagClient(),
        uow=uow,
    )
    service.run_scan(problem_id=problem_id, min_similarity=min_similarity)

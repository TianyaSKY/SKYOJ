"""剽窃检测 HTTP 接口。"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_plagiarism_service
from app.api.schemas.plagiarism import BatchCheckBody
from app.domain.plagiarism import BatchCheckParams
from app.services.plagiarism_facade_service import PlagiarismFacadeService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


def _log_response(item) -> dict:
    return {"id": item.id, "submission_id": item.submission_id, "target_submission_id": item.target_submission_id, "similarity_score": item.similarity_score, "problem_id": item.problem_id, "exam_id": item.exam_id, "user_id": item.user_id, "username": item.username, "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else None}


@router.get("/logs")
def get_plagiarism_logs(problem_id: int | None = None, exam_id: int | None = None, min_score: float = Query(default=0.0, ge=0), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), auth: AuthContext = Depends(get_current_auth), service: PlagiarismFacadeService = Depends(get_plagiarism_service)):
    result = service.list_logs(auth.user.role, problem_id, exam_id, min_score, page, page_size)
    return {"total": result.total, "pages": (result.total + result.page_size - 1) // result.page_size if result.total else 0, "current_page": result.page, "page_size": result.page_size, "data": [_log_response(item) for item in result.items]}


@router.get("/logs/{submission_id}")
def get_submission_plagiarism_log(submission_id: int, auth: AuthContext = Depends(get_current_auth), service: PlagiarismFacadeService = Depends(get_plagiarism_service)):
    return _log_response(service.get_log(submission_id, auth.user.id, auth.user.role))


@router.post("/check_batch", status_code=202)
def trigger_batch_check(body: BatchCheckBody, auth: AuthContext = Depends(get_current_auth), service: PlagiarismFacadeService = Depends(get_plagiarism_service)):
    service.start_batch_check(auth.user.role, BatchCheckParams(body.submission_ids))
    return {"message": "Batch plagiarism check started"}


@router.delete("/logs/{log_id}")
def delete_plagiarism_log(log_id: int, auth: AuthContext = Depends(get_current_auth), service: PlagiarismFacadeService = Depends(get_plagiarism_service)):
    service.delete_log(auth.user.role, log_id)
    return {"message": "Log deleted"}

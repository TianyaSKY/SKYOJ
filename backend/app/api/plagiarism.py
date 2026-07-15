from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.plagiarism import PlagiarismLog
from app.models.submission import Submission
from app.utils.auth_tools import AuthContext, get_current_auth
from app.utils.feature_flags import ENABLE_PLAGIARISM
from app.utils.pagination import paginate

router = APIRouter()


@router.get("/logs")
def get_plagiarism_logs(
    problem_id: Optional[int] = None,
    exam_id: Optional[int] = None,
    min_score: float = 0.0,
    page: int = 1,
    page_size: int = 20,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    query = db.query(PlagiarismLog).join(
        Submission, PlagiarismLog.submission_id == Submission.id
    )

    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)
    if exam_id:
        query = query.filter(Submission.exam_id == exam_id)
    if min_score > 0:
        query = query.filter(PlagiarismLog.similarity_score >= min_score)

    query = query.order_by(PlagiarismLog.similarity_score.desc())
    items, total, pages = paginate(query, page=page, per_page=page_size)

    logs_data = []
    for log in items:
        logs_data.append(
            {
                "id": log.id,
                "submission_id": log.submission_id,
                "target_submission_id": log.target_submission_id,
                "similarity_score": round(log.similarity_score, 2),
                "problem_id": log.submission.problem_id,
                "exam_id": log.submission.exam_id,
                "user_id": log.submission.user_id,
                "username": log.submission.user.username,
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return {
        "total": total,
        "pages": pages,
        "current_page": page,
        "page_size": page_size,
        "data": logs_data,
    }


@router.get("/logs/{submission_id}")
def get_submission_plagiarism_log(
    submission_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    log = (
        db.query(PlagiarismLog).filter_by(submission_id=submission_id).first()
    )
    if not log:
        raise HTTPException(
            status_code=404, detail={"error": "Plagiarism log not found"}
        )

    if (
        auth.user.role == "student"
        and log.submission.user_id != auth.user.id
    ):
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    return {
        "id": log.id,
        "submission_id": log.submission_id,
        "target_submission_id": log.target_submission_id,
        "similarity_score": round(log.similarity_score, 2),
        "problem_id": log.submission.problem_id,
        "exam_id": log.submission.exam_id,
        "user_id": log.submission.user_id,
        "username": log.submission.user.username,
        "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.post("/check_batch", status_code=202)
def trigger_batch_check(
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})
    if not ENABLE_PLAGIARISM:
        raise HTTPException(
            status_code=503,
            detail={"error": "Plagiarism service is temporarily disabled"},
        )

    submission_ids = data.get("submission_ids", [])
    if not submission_ids:
        raise HTTPException(
            status_code=400, detail={"error": "No submission_ids provided"}
        )

    from app.services.plagiarism_service import plagiarism_service

    plagiarism_service.start_check_task(submission_ids)
    return {"message": "Batch plagiarism check started"}


@router.delete("/logs/{log_id}")
def delete_plagiarism_log(
    log_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    log = db.get(PlagiarismLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    db.delete(log)
    db.commit()
    return {"message": "Log deleted"}

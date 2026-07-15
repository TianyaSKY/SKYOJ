import os
from datetime import datetime
from threading import Thread
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.exam import Exam
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.services.judge_service import judge_submission
from app.utils.auth_tools import AuthContext, get_current_auth
from app.utils.feature_flags import ENABLE_PLAGIARISM
from app.utils.files import secure_filename
from app.utils.pagination import paginate

router = APIRouter()
UPLOAD_SUBMISSION_DIR = "uploads/submissions"


@router.post("/submit", status_code=202)
async def submit_code(
    request: Request,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
    problem_id: Optional[int] = Form(default=None),
    code: Optional[str] = Form(default=None),
    language: Optional[str] = Form(default=None),
    exam_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
):
    content_type = request.headers.get("content-type", "")
    user_code = None
    exam_id_val = -1
    lang = language
    pid = problem_id

    if "application/json" in content_type:
        data = await request.json()
        pid = data.get("problem_id")
        user_code = data.get("code")
        lang = data.get("language")
        exam_id_val = data.get("exam_id", -1)
    else:
        pid = problem_id
        lang = language
        user_code = code or ""
        exam_id_val = exam_id if exam_id is not None else -1

        if file and file.filename:
            if lang == "csv" or file.filename.endswith(".csv"):
                os.makedirs(UPLOAD_SUBMISSION_DIR, exist_ok=True)
                filename = secure_filename(
                    f"{auth.user.id}_{pid}_{file.filename}"
                )
                file_path = os.path.join(UPLOAD_SUBMISSION_DIR, filename)
                content = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                user_code = file_path
            else:
                raw = await file.read()
                user_code = raw.decode("utf-8")

    if not pid or not user_code:
        raise HTTPException(
            status_code=400, detail={"error": "Missing problem_id or code/file"}
        )

    try:
        exam_id_val = int(exam_id_val)
    except (ValueError, TypeError):
        exam_id_val = -1

    if exam_id_val != -1:
        now = datetime.now()
        exam = (
            db.query(Exam)
            .filter(
                Exam.id == exam_id_val,
                Exam.start_time <= now,
                Exam.end_time >= now,
            )
            .first()
        )
        if not exam:
            exam_id_val = -1

    user_id = auth.user.id
    db_exam_id = exam_id_val if exam_id_val != -1 else None

    problem = db.get(Problem, pid)
    if not problem:
        raise HTTPException(status_code=404, detail={"error": "Problem not found"})

    new_submission = Submission(
        user_id=user_id,
        problem_id=pid,
        exam_id=db_exam_id,
        language=lang,
        code_content=user_code,
        status="Pending",
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)

    Thread(
        target=judge_submission,
        args=(
            new_submission.id,
            str(problem.type),
            user_code,
            pid,
            lang,
        ),
    ).start()

    return {
        "message": "Submission received, judging in background.",
        "submission_id": new_submission.id,
        "status": "Pending",
        "exam_id": db_exam_id,
    }


@router.get("")
def list_submissions(
    problem_id: Optional[int] = None,
    user_id: Optional[int] = None,
    exam_id: Optional[int] = None,
    status: Optional[str] = None,
    username: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    query = db.query(Submission)

    if auth.user.role == "student":
        query = query.filter(Submission.user_id == auth.user.id)
    elif user_id:
        query = query.filter(Submission.user_id == user_id)

    if username:
        query = query.join(User).filter(User.username.like(f"%{username}%"))
    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)
    if exam_id:
        query = query.filter(Submission.exam_id == exam_id)
    if status:
        query = query.filter(Submission.status == status)

    query = query.order_by(Submission.created_at.desc())
    submissions, total, pages = paginate(query, page=page, per_page=per_page)

    return {
        "total": total,
        "pages": pages,
        "current_page": page,
        "submissions": [
            {
                "id": s.id,
                "user_id": s.user_id,
                "username": s.user.username,
                "problem_id": s.problem_id,
                "exam_id": s.exam_id,
                "status": s.status,
                "score": s.score,
                "language": s.language,
                "created_at": s.created_at.isoformat(),
            }
            for s in submissions
        ],
    }


@router.get("/{submission_id}")
def get_submission(
    submission_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail={"error": "Submission not found"})

    if auth.user.role == "student" and submission.user_id != auth.user.id:
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    return {
        "id": submission.id,
        "status": submission.status,
        "score": submission.score,
        "log": submission.output_log,
        "code": submission.code_content,
        "language": submission.language,
        "exam_id": submission.exam_id,
        "created_at": submission.created_at.isoformat(),
    }


@router.post("/{submission_id}/check_plagiarism", status_code=202)
def check_single_submission_plagiarism(
    submission_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})
    if not ENABLE_PLAGIARISM:
        raise HTTPException(
            status_code=503,
            detail={"error": "Plagiarism service is temporarily disabled"},
        )

    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    from app.services.plagiarism_service import plagiarism_service

    plagiarism_service.start_check_task([submission.id])

    return {
        "message": f"Plagiarism check started for submission #{submission_id}."
    }

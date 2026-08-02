from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.api.deps import get_submission_service
from app.api.schemas.submission import SubmitCodeBody
from app.domain.submission import SubmissionQuery, SubmitParams
from app.services.submission_service import SubmissionService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()
@router.post("/submit", status_code=202)
async def submit_code(
    request: Request,
    auth: AuthContext = Depends(get_current_auth),
    service: SubmissionService = Depends(get_submission_service),
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
        body = SubmitCodeBody.model_validate(await request.json())
        pid = body.problem_id
        user_code = body.code
        lang = body.language
        exam_id_val = body.exam_id if body.exam_id is not None else -1
    else:
        pid = problem_id
        lang = language
        user_code = code or ""
        exam_id_val = exam_id if exam_id is not None else -1

        if file and file.filename:
            if lang == "csv" or file.filename.endswith(".csv"):
                content = await file.read()
                user_code = "__file_upload__"
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

    result = service.submit(
        SubmitParams(
            user_id=auth.user.id, problem_id=pid, code=user_code,
            language=lang or "", exam_id=exam_id_val,
            is_file_upload=bool(file and file.filename and (lang == "csv" or file.filename.endswith(".csv"))),
            filename=file.filename if file else None,
            file_content=content if file and file.filename and (lang == "csv" or file.filename.endswith(".csv")) else None,
        )
    )

    return {
        "message": "Submission received, judging in background.",
        "submission_id": result.submission_id,
        "status": result.status,
        "exam_id": result.exam_id,
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
    service: SubmissionService = Depends(get_submission_service),
):
    result = service.list_submissions(SubmissionQuery(
        requester_id=auth.user.id, requester_role=auth.user.role,
        problem_id=problem_id, user_id=user_id, exam_id=exam_id, status=status,
        username=username, page=page, page_size=per_page,
    ))

    return {
        "total": result.total,
        "pages": result.pages,
        "current_page": result.current_page,
        "submissions": [
            {
                "id": s.id,
                "user_id": s.user_id,
                "username": s.username,
                "problem_id": s.problem_id,
                "exam_id": s.exam_id,
                "status": s.status,
                "score": s.score,
                "language": s.language,
                "created_at": s.created_at.isoformat(),
            }
            for s in result.submissions
        ],
    }


@router.get("/{submission_id}")
def get_submission(
    submission_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: SubmissionService = Depends(get_submission_service),
):
    submission = service.get_submission(submission_id, auth.user.id, auth.user.role)

    return {
        "id": submission.id,
        "status": submission.status,
        "score": submission.score,
        "log": submission.log,
        "code": submission.code,
        "language": submission.language,
        "exam_id": submission.exam_id,
        "created_at": submission.created_at.isoformat(),
    }

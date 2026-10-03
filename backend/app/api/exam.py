"""考试 HTTP 接口。"""

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_exam_service
from app.api.schemas.common import MessageResponse
from app.api.schemas.exam import (
    AddProblemToExamBody,
    CreateExamBody,
    EnterExamBody,
    EnterExamResponse,
    ExamDetailResponse,
    ExamListResponse,
    ExamProblemStatusResponse,
    ExamResponse,
    ExamTokenResponse,
    MonitorResponse,
    RankResponse,
    UpdateExamBody,
)
from app.core.auth_tokens import encode_auth_token
from app.services.exam import (
    AddExamProblemParams,
    CreateExamParams,
    EnterExamParams,
    ExamService,
    UpdateExamParams,
)

router = APIRouter()


def _exam_response(exam) -> dict:
    return {
        "id": exam.id,
        "title": exam.title,
        "description": exam.description,
        "start_time": exam.start_time.isoformat(),
        "end_time": exam.end_time.isoformat(),
        "contest_type": exam.contest_type,
        "freeze_minutes": exam.freeze_minutes,
        "is_visible": exam.is_visible,
        "created_by": exam.created_by,
    }


@router.post("/", status_code=201, response_model=ExamResponse)
def create_exam(
    body: CreateExamBody,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    exam = service.create_exam(
        auth.user.role,
        CreateExamParams(
            title=body.title,
            description=body.description,
            start_time=body.start_time,
            end_time=body.end_time,
            contest_type=body.contest_type,
            freeze_minutes=body.freeze_minutes,
            password=body.password,
            is_visible=body.is_visible,
            created_by=auth.user.id,
        ),
    )
    return _exam_response(exam)


@router.get("/", response_model=list[ExamListResponse])
def get_exams(
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    return [
        {
            **_exam_response(item),
            "problem_count": item.problem_count,
            "submission_count": item.submission_count,
        }
        for item in service.list_exams(auth.user.role)
    ]


@router.post("/exit", response_model=ExamTokenResponse)
def exit_exam(auth: AuthContext = Depends(get_current_auth)):
    return {
        "message": "Successfully exited exam",
        "token": encode_auth_token(auth.user.id, auth.user.role, -1),
    }


@router.get("/status", response_model=list[ExamProblemStatusResponse])
def get_my_exam_status(
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    return [
        {
            "problem_id": item.problem_id,
            "display_id": item.display_id,
            "title": item.title,
            "max_score": item.max_score,
            "status": item.status,
            "current_score": item.current_score,
            "last_submitted_at": item.last_submitted_at.isoformat()
            if item.last_submitted_at
            else None,
        }
        for item in service.get_status(auth.user.id, auth.exam_id)
    ]


@router.get("/{exam_id}", response_model=ExamDetailResponse)
def get_exam_detail(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    exam = service.get_detail(exam_id, auth.user.role, auth.exam_id)
    return {
        **_exam_response(exam),
        "has_password": exam.has_password,
        "problems": [
            {
                "problem_id": item.problem_id,
                "display_id": item.display_id,
                "score": item.score,
                "title": item.title,
            }
            for item in exam.problems
        ],
    }


@router.post("/{exam_id}/enter", response_model=EnterExamResponse)
def enter_exam(
    exam_id: int,
    body: EnterExamBody | None = None,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    target_id = service.enter_exam(
        auth.user.role,
        auth.user.id,
        auth.exam_id,
        EnterExamParams(exam_id, body.password if body else None),
    )
    return {
        "message": "Successfully entered exam",
        "token": encode_auth_token(auth.user.id, auth.user.role, target_id),
        "exam_id": target_id,
    }


@router.get("/{exam_id}/monitor", response_model=MonitorResponse)
def get_exam_monitor(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    result = service.monitor(auth.user.role, exam_id)
    return {
        "exam_title": result.exam_title,
        "problems": [
            {
                "problem_id": p.problem_id,
                "display_id": p.display_id,
                "max_score": p.max_score,
            }
            for p in result.problems
        ],
        "users": [
            {
                "user_id": user.user_id,
                "username": user.username,
                "total_score": user.total_score,
                "submissions": {
                    problem_id: {
                        "submission_id": item.submission_id,
                        "status": item.status,
                        "score": item.score,
                        "time": item.time,
                    }
                    for problem_id, item in user.submissions.items()
                },
            }
            for user in result.users
        ],
    }


@router.get("/{exam_id}/rank", response_model=RankResponse)
def get_exam_rank(
    exam_id: int,
    as_of: Optional[str] = None,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    result = service.rank(exam_id, auth.user.role, auth.exam_id, as_of=as_of)
    return {
        "exam_title": result.exam_title,
        "problems": [
            {"problem_id": p.problem_id, "display_id": p.display_id}
            for p in result.problems
        ],
        "rank": [
            {
                "user_id": user.user_id,
                "username": user.username,
                "solved": user.solved,
                "penalty": user.penalty,
                "problems": {
                    problem_id: {
                        "solved": item.solved,
                        "failed_attempts": item.failed_attempts,
                        "time": item.time,
                    }
                    for problem_id, item in user.problems.items()
                },
            }
            for user in result.rank
        ],
    }


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    body: UpdateExamBody,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    exam = service.update_exam(
        auth.user.role,
        exam_id,
        UpdateExamParams(
            title=body.title,
            description=body.description,
            start_time=body.start_time,
            end_time=body.end_time,
            contest_type=body.contest_type,
            freeze_minutes=body.freeze_minutes,
            password=body.password,
            is_visible=body.is_visible,
        ),
    )
    return _exam_response(exam)


@router.delete("/{exam_id}", response_model=MessageResponse)
def delete_exam(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    service.delete_exam(auth.user.role, exam_id)
    return {"message": "Exam deleted"}


@router.post("/{exam_id}/problems", status_code=201, response_model=MessageResponse)
def add_problem_to_exam(
    exam_id: int,
    body: AddProblemToExamBody,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    service.add_problem(
        auth.user.role,
        exam_id,
        AddExamProblemParams(body.problem_id, body.display_id, body.score),
    )
    return {"message": "Problem added to exam"}


@router.delete("/{exam_id}/problems/{problem_id}", response_model=MessageResponse)
def remove_problem_from_exam(
    exam_id: int,
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    service.remove_problem(auth.user.role, exam_id, problem_id)
    return {"message": "Problem removed from exam"}


@router.get("/{exam_id}/export_scores", response_model=None)
def export_exam_scores(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ExamService = Depends(get_exam_service),
):
    exam, rows = service.score_rows(auth.user.role, exam_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "User ID",
            "Username",
            *[f"{item.display_id} (Max: {item.score})" for item in exam.problems],
            "Total Score",
        ]
    )
    for row in rows:
        writer.writerow([row.user_id, row.username, *row.scores, row.total_score])
    filename = f"exam_{exam_id}_scores_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import get_problem_service
from app.api.schemas.problem import CreateProblemBody, UpdateProblemBody
from app.domain.problem import CreateProblemParams, PaginatedProblems, UpdateProblemParams, UploadTestCasesParams
from app.services.problem_service import ProblemService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.post("/", status_code=201)
def create_problem(
    body: CreateProblemBody,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    new_problem = service.create_problem(
        auth.user.role,
        CreateProblemParams(
            title=body.title,
            content=body.content,
            language=body.language,
            problem_type=body.type,
            time_limit=body.time_limit,
            memory_limit=body.memory_limit,
            template_code=body.template_code,
        )
    )

    return {
        "message": "Problem created successfully",
        "problem_id": new_problem.id,
    }


@router.get("/")
def get_problems(
    page: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    result = service.list_problems(auth.user.role, page=page, page_size=page_size)
    if isinstance(result, PaginatedProblems):
        return {
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
            "problems": [
                {
                    "id": p.id,
                    "title": p.title,
                    "type": p.problem_type,
                    "language": p.language,
                    "time_limit": p.time_limit,
                    "memory_limit": p.memory_limit,
                }
                for p in result.problems
            ],
        }

    return [
        {
            "id": p.id,
            "title": p.title,
            "type": p.problem_type,
            "language": p.language,
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit,
        }
        for p in result
    ]


@router.get("/{problem_id}")
def get_problem(
    problem_id: int,
    service: ProblemService = Depends(get_problem_service),
):
    problem = service.get_problem(problem_id)
    return {
        "id": problem.id,
        "title": problem.title,
        "content": problem.content,
        "type": problem.problem_type,
        "language": problem.language,
        "time_limit": problem.time_limit,
        "memory_limit": problem.memory_limit,
        "template_code": problem.template_code,
    }


@router.put("/{problem_id}")
def update_problem(
    problem_id: int,
    body: UpdateProblemBody,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    service.update_problem(
        auth.user.role,
        problem_id,
        UpdateProblemParams(
            title=body.title,
            content=body.content,
            language=body.language,
            problem_type=body.type,
            time_limit=body.time_limit,
            memory_limit=body.memory_limit,
            template_code=body.template_code,
        ),
    )
    return {"message": "Problem updated successfully"}


@router.delete("/{problem_id}")
def delete_problem(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    service.delete_problem(auth.user.role, problem_id)
    return {"message": "Problem deleted successfully"}


@router.post("/{problem_id}/upload_files")
async def upload_files(
    problem_id: int,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    files = service.upload_test_cases(
        auth.user.role,
        UploadTestCasesParams(problem_id, file.filename or "", await file.read()),
    )
    return {"message": f"Test cases for problem {problem_id} uploaded and extracted successfully.", "files": files}


@router.delete("/{problem_id}/test_cases")
def delete_test_cases(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    service.delete_test_cases(auth.user.role, problem_id)
    return {"message": f"All test cases for problem {problem_id} deleted."}


@router.get("/{problem_id}/test_cases")
def download_test_cases(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    content = service.download_test_cases(auth.user.role, problem_id)
    return StreamingResponse(
        iter([content]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="problem_{problem_id}_test_cases.zip"'
        },
    )

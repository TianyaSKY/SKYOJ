from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_problem_service
from app.api.schemas.common import MessageResponse
from app.api.schemas.problem import (
    CreateProblemBody,
    CreateProblemResponse,
    PaginatedProblemsResponse,
    ProblemDetailResponse,
    ProblemListResponse,
    TestCaseSummaryResponse,
    UpdateProblemBody,
    UploadTestCasesResponse,
)
from app.services.problem import (
    CreateProblemParams,
    PaginatedProblems,
    ProblemService,
    UpdateProblemParams,
    UploadTestCasesParams,
)

router = APIRouter()


@router.post("/", status_code=201, response_model=CreateProblemResponse)
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
        ),
    )

    return {
        "message": "Problem created successfully",
        "problem_id": new_problem.id,
    }


@router.get("/", response_model=list[ProblemListResponse] | PaginatedProblemsResponse)
def get_problems(
    page: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    tag_id: Optional[int] = Query(default=None),
    problem_type: Literal["acm", "oop", "kaggle"] | None = Query(default=None),
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    result = service.list_problems(
        auth.user.role, page=page, page_size=page_size, tag_id=tag_id,
        problem_type=problem_type,
    )
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
                    "test_case_status": p.test_case_status,
                    "test_case_count": p.test_case_count,
                    "test_case_valid_count": p.test_case_valid_count,
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
            "test_case_status": p.test_case_status,
            "test_case_count": p.test_case_count,
            "test_case_valid_count": p.test_case_valid_count,
        }
        for p in result
    ]


@router.get("/{problem_id}", response_model=ProblemDetailResponse)
def get_problem(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    del auth
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


@router.put("/{problem_id}", response_model=MessageResponse)
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


@router.delete("/{problem_id}", response_model=MessageResponse)
def delete_problem(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    service.delete_problem(auth.user.role, problem_id)
    return {"message": "Problem deleted successfully"}


@router.post("/{problem_id}/upload_files", response_model=UploadTestCasesResponse)
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
    return {
        "message": f"Test cases for problem {problem_id} uploaded and extracted successfully.",
        "files": files,
    }


@router.delete("/{problem_id}/test_cases", response_model=MessageResponse)
def delete_test_cases(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    service.delete_test_cases(auth.user.role, problem_id)
    return {"message": f"All test cases for problem {problem_id} deleted."}


@router.get("/{problem_id}/test_cases/summary", response_model=TestCaseSummaryResponse)
def get_test_case_summary(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: ProblemService = Depends(get_problem_service),
):
    summary = service.get_test_case_summary(auth.user.role, problem_id)
    return {
        "status": summary.status,
        "total_count": summary.total_count,
        "valid_count": summary.valid_count,
        "invalid_count": summary.invalid_count,
        "file_count": summary.file_count,
        "total_size": summary.total_size,
        "ignored_files": summary.ignored_files,
        "cases": [
            {
                "name": case.name,
                "input_file": case.input_file,
                "output_file": case.output_file,
                "input_size": case.input_size,
                "output_size": case.output_size,
                "status": case.status,
            }
            for case in summary.cases
        ],
    }


@router.get("/{problem_id}/test_cases", response_model=None)
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

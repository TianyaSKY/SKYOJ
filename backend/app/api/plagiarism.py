"""查重 API 路由。"""

from fastapi import APIRouter, Depends, Path, Query

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_plagiarism_service
from app.api.schemas.plagiarism import (
    PlagiarismListResponse,
    PlagiarismReportResponse,
    PlagiarismScanResponse,
)
from app.services.plagiarism import PlagiarismService

router = APIRouter()


@router.get("/reports/{submission_id}", response_model=list[PlagiarismReportResponse])
def get_submission_reports(
    submission_id: int = Path(ge=1),
    auth: AuthContext = Depends(get_current_auth),
    service: PlagiarismService = Depends(get_plagiarism_service),
):
    """获取某提交的所有查重报告。

    学生只能查看自己的提交；教师可查看任意提交。
    """
    reports = service.get_submission_reports(
        submission_id, auth.user.id, auth.user.role
    )
    return reports


@router.get("/problem/{problem_id}", response_model=PlagiarismListResponse)
def list_problem_reports(
    problem_id: int = Path(ge=1),
    min_score: float = Query(default=0.3, ge=0, le=1),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_auth),
    service: PlagiarismService = Depends(get_plagiarism_service),
):
    """列出某题目的所有查重报告（按相似度降序）。"""
    result = service.get_problem_reports(
        problem_id, min_score, page, per_page, auth.user.id, auth.user.role
    )
    return result


@router.post("/scan/{problem_id}", response_model=PlagiarismScanResponse)
def trigger_plagiarism_scan(
    problem_id: int = Path(ge=1),
    auth: AuthContext = Depends(get_current_auth),
    service: PlagiarismService = Depends(get_plagiarism_service),
):
    """手动触发某题目的代码查重扫描（仅教师可操作）。"""
    job_id = service.trigger_manual_scan(problem_id, auth.user.role)
    return PlagiarismScanResponse(job_id=job_id, message="查重任务已入队")

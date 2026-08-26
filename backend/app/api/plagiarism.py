"""查重 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_plagiarism_service
from app.api.schemas.plagiarism import (
    PlagiarismListResponse,
    PlagiarismReportResponse,
    PlagiarismScanResponse,
)
from app.services.plagiarism_service import PlagiarismService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.get("/reports/{submission_id}", response_model=list[PlagiarismReportResponse])
def get_submission_reports(
    submission_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: PlagiarismService = Depends(get_plagiarism_service),
):
    """获取某提交的所有查重报告。

    学生只能查看自己的提交；教师可查看任意提交。
    """
    reports = service.get_submission_reports(
        submission_id, auth.user.id, auth.user.role
    )
    return [_to_report_response(r) for r in reports]


@router.get("/problem/{problem_id}", response_model=PlagiarismListResponse)
def list_problem_reports(
    problem_id: int,
    min_score: float = 0.3,
    page: int = 1,
    per_page: int = 20,
    auth: AuthContext = Depends(get_current_auth),
    service: PlagiarismService = Depends(get_plagiarism_service),
):
    """列出某题目的所有查重报告（按相似度降序）。"""
    if auth.user.role != "teacher":
        raise HTTPException(403, "仅教师可查看题目整体查重报告")
    result = service.get_problem_reports(
        problem_id, min_score, page, per_page, auth.user.id, auth.user.role
    )
    result["reports"] = [_to_report_response(r) for r in result["reports"]]
    return result


@router.post("/scan/{problem_id}", response_model=PlagiarismScanResponse)
def trigger_plagiarism_scan(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: PlagiarismService = Depends(get_plagiarism_service),
):
    """手动触发某题目的代码查重扫描（仅教师可操作）。"""
    if auth.user.role != "teacher":
        raise HTTPException(403, "仅教师可触发查重扫描")
    from app.database import get_db
    db_gen = get_db()
    db = next(db_gen)
    try:
        job_id = service.trigger_manual_scan(db, problem_id)
    finally:
        db.close()
    return PlagiarismScanResponse(job_id=job_id, message="查重任务已入队")


def _to_report_response(r: dict) -> PlagiarismReportResponse:
    from app.api.schemas.plagiarism import MatchedBlockResponse

    return PlagiarismReportResponse(
        id=r["id"],
        submission_a_id=r["submission_a_id"],
        submission_b_id=r["submission_b_id"],
        username_a=r["username_a"],
        username_b=r["username_b"],
        similarity_score=r["similarity_score"],
        matched_blocks=[
            MatchedBlockResponse(
                start_a=b["start_a"],
                end_a=b["end_a"],
                start_b=b["start_b"],
                end_b=b["end_b"],
                code_a=b["code_a"],
                code_b=b["code_b"],
            )
            for b in (r["matched_blocks"] or [])
        ],
        status=r["status"],
        created_at=r["created_at"],
    )

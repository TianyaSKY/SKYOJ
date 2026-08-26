"""学情分析 HTTP 接口（教师专用）。"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_submission_service
from app.services.submission_service import SubmissionService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.get("/admin/analytics")
def get_analytics(
    auth: AuthContext = Depends(get_current_auth),
    service: SubmissionService = Depends(get_submission_service),
):
    """平台全局学情分析数据（仅教师可访问）。"""
    if auth.user.role != "teacher":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="仅教师可访问")

    return service.get_platform_analytics()

"""学情分析 HTTP 接口（教师专用）。"""

from fastapi import APIRouter, Depends

from app.api.deps import get_submission_service
from app.api.schemas.analytics import PlatformAnalyticsResponse
from app.services.submission import SubmissionService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.get("/admin/analytics", response_model=PlatformAnalyticsResponse)
def get_analytics(
    auth: AuthContext = Depends(get_current_auth),
    service: SubmissionService = Depends(get_submission_service),
):
    """平台全局学情分析数据（仅教师可访问）。"""
    return service.get_platform_analytics(auth.user.role)

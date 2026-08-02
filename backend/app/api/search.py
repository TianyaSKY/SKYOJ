"""题目关键词搜索 HTTP 接口。"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_search_service
from app.services.search_facade_service import SearchFacadeService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.get("")
def search_problems(
    query: str = Query(default="", max_length=255),
    top_k: int = Query(default=5, ge=1, le=50),
    auth: AuthContext = Depends(get_current_auth),
    service: SearchFacadeService = Depends(get_search_service),
):
    return service.search(auth.user.id, query, top_k)

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
    return [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "type": p.problem_type,
            "language": p.language,
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit,
        }
        for p in service.search(auth.user.id, query, top_k)
    ]

"""题目关键词搜索 HTTP 接口。"""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_search_service
from app.api.schemas.problem import SearchProblemResponse
from app.services.search import SearchFacadeService

router = APIRouter()


@router.get("", response_model=list[SearchProblemResponse])
def search_problems(
    query: str = Query(default="", max_length=255),
    top_k: int = Query(default=5, ge=1, le=50),
    tag_id: int | None = Query(default=None, ge=1),
    problem_type: Literal["acm", "oop", "kaggle"] | None = Query(default=None),
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
        for p in service.search(
            auth.user.id, query, top_k, auth.user.role,
            tag_id=tag_id, problem_type=problem_type,
        )
    ]

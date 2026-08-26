"""错题本 HTTP 接口。"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import get_wrong_book_service
from app.domain.wrong_book import WrongBookItem, WrongBookStats
from app.services.wrong_book_service import WrongBookService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.get("/wrong-book/stats")
def get_wrong_book_stats(
    auth: AuthContext = Depends(get_current_auth),
    service: WrongBookService = Depends(get_wrong_book_service),
) -> WrongBookStats:
    stats = service.get_stats(auth.user.id)
    return {
        "total": stats.total,
        "unresolved": stats.unresolved,
        "reviewed": stats.reviewed,
        "accepted": stats.accepted,
    }


@router.get("/wrong-book/")
def list_wrong_book(
    auth: AuthContext = Depends(get_current_auth),
    service: WrongBookService = Depends(get_wrong_book_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unresolved_only: bool = Query(default=False),
):
    items, total = service.list_for_user(
        auth.user.id,
        unresolved_only=unresolved_only,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "problem_id": item.problem_id,
                "problem_title": item.problem_title,
                "submission_id": item.submission_id,
                "first_wrong_at": item.first_wrong_at.isoformat() if item.first_wrong_at else None,
                "latest_wrong_at": item.latest_wrong_at.isoformat() if item.latest_wrong_at else None,
                "accepted": item.accepted,
                "reviewed": item.reviewed,
            }
            for item in items
        ],
    }


@router.post("/wrong-book/{entry_id}/toggle-review")
def toggle_reviewed(
    entry_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: WrongBookService = Depends(get_wrong_book_service),
):
    result = service.toggle_reviewed(entry_id, auth.user.id)
    return {"id": result.id, "reviewed": result.reviewed}

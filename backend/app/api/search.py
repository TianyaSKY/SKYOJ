from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.problem import Problem
from app.models.search_history import SearchHistory
from app.utils.auth_tools import AuthContext, get_current_auth
from app.utils.feature_flags import ENABLE_SEMANTIC_SEARCH

router = APIRouter()


def _normal_search(db: Session, query: str, top_k: int):
    problems = (
        db.query(Problem)
        .filter(
            or_(
                Problem.title.like(f"%{query}%"),
                Problem.content.like(f"%{query}%"),
            )
        )
        .limit(top_k)
        .all()
    )
    return [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "type": p.type,
            "language": p.language,
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit,
        }
        for p in problems
    ]


@router.get("")
def search_problems(
    query: str = "",
    mode: str = "semantic",
    top_k: int = 5,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if not query:
        return []

    try:
        search_history = SearchHistory(user_id=auth.user.id, query=query)
        db.add(search_history)
        db.commit()
    except Exception as e:
        print(f"Error saving search history: {e}")
        db.rollback()

    if mode == "normal":
        return _normal_search(db, query, top_k)

    if not ENABLE_SEMANTIC_SEARCH:
        return _normal_search(db, query, top_k)

    from app.services.search_service import search_service

    return search_service.search(query, top_k=top_k)


@router.post("/rebuild")
def rebuild_index(auth: AuthContext = Depends(get_current_auth)):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})
    if not ENABLE_SEMANTIC_SEARCH:
        raise HTTPException(
            status_code=503,
            detail={"error": "Semantic search is temporarily disabled"},
        )

    from app.services.search_service import search_service

    search_service.rebuild_index()
    return {"message": "Index rebuilt successfully"}

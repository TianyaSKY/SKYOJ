"""题解、标签、点赞、评论的 REST 接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_solution_service, get_tag_service
from app.api.schemas.problem_community import (
    AttachTagRequest,
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    CreateSolutionRequest,
    CreateTagRequest,
    SolutionDetailResponse,
    SolutionListItemResponse,
    SolutionListResponse,
    TagResponse,
    ToggleFavoriteResponse,
    ToggleLikeResponse,
    UpdateSolutionRequest,
)
from app.services.community import SolutionService, TagService

router = APIRouter(prefix="/problems", tags=["community"])


# === 题解 ===


@router.get("/{problem_id}/solutions", response_model=SolutionListResponse)
def list_solutions(
    problem_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    items, total = service.list_for_problem(problem_id, auth.user.id, page, page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            SolutionListItemResponse(
                id=i.id,
                problem_id=i.problem_id,
                author_id=i.author_id,
                author_username=i.author_username,
                title=i.title,
                language=i.language,
                is_official=i.is_official,
                vote_count=i.vote_count,
                comment_count=i.comment_count,
                created_at=i.created_at,
            )
            for i in items
        ],
    }


@router.post(
    "/{problem_id}/solutions",
    response_model=SolutionDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_solution(
    problem_id: int,
    payload: CreateSolutionRequest,
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    from app.services.community import CreateSolutionParams

    detail = service.create(
        CreateSolutionParams(
            problem_id=problem_id,
            author_id=auth.user.id,
            title=payload.title,
            content=payload.content,
            language=payload.language,
        )
    )
    return SolutionDetailResponse(**_detail_to_dict(detail))


@router.get("/solutions/{solution_id}", response_model=SolutionDetailResponse)
def get_solution(
    solution_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    detail = service.get(solution_id, auth.user.id)
    return SolutionDetailResponse(**_detail_to_dict(detail))


@router.put("/solutions/{solution_id}", response_model=SolutionDetailResponse)
def update_solution(
    solution_id: int,
    payload: UpdateSolutionRequest,
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    from app.services.community import UpdateSolutionParams

    detail = service.update(
        UpdateSolutionParams(
            solution_id=solution_id,
            requester_id=auth.user.id,
            requester_role=auth.user.role,
            title=payload.title,
            content=payload.content,
            language=payload.language,
            is_official=payload.is_official,
        )
    )
    return SolutionDetailResponse(**_detail_to_dict(detail))


@router.delete(
    "/solutions/{solution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def hide_solution(
    solution_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    service.hide(solution_id, auth.user.id, auth.user.role)
    return None


@router.post("/solutions/{solution_id}/like", response_model=ToggleLikeResponse)
def toggle_like(
    solution_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    result = service.toggle_like(solution_id, auth.user.id)
    return ToggleLikeResponse(
        solution_id=result.solution_id,
        liked=result.liked,
        vote_count=result.vote_count,
    )


@router.post("/solutions/{solution_id}/favorite", response_model=ToggleFavoriteResponse)
def toggle_favorite(
    solution_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    result = service.toggle_favorite(solution_id, auth.user.id)
    return ToggleFavoriteResponse(
        solution_id=result.solution_id,
        favorited=result.favorited,
    )


# === 评论 ===


@router.post(
    "/solutions/{solution_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    solution_id: int,
    payload: CreateCommentRequest,
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    from app.services.community import CreateCommentParams

    comment = service.add_comment(
        CreateCommentParams(
            solution_id=solution_id, user_id=auth.user.id, content=payload.content
        )
    )
    return CommentResponse(
        id=comment.id,
        solution_id=comment.solution_id,
        user_id=comment.user_id,
        username=comment.username,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/solutions/{solution_id}/comments", response_model=CommentListResponse)
def list_comments(
    solution_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SolutionService = Depends(get_solution_service),
):
    items, total = service.list_comments(solution_id, page, page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            CommentResponse(
                id=c.id,
                solution_id=c.solution_id,
                user_id=c.user_id,
                username=c.username,
                content=c.content,
                created_at=c.created_at,
            )
            for c in items
        ],
    }


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_comment(
    comment_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: SolutionService = Depends(get_solution_service),
):
    service.delete_comment(comment_id, auth.user.id, auth.user.role)
    return None


# === 标签 ===


tags_router = APIRouter(prefix="/tags", tags=["community"])


@tags_router.get("", response_model=list[TagResponse])
def list_tags(service: TagService = Depends(get_tag_service)):
    items = service.list_all()
    return [TagResponse(**_tag_to_dict(t)) for t in items]


@tags_router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: CreateTagRequest,
    auth: AuthContext = Depends(get_current_auth),
    service: TagService = Depends(get_tag_service),
):
    from app.services.community import CreateTagParams

    tag = service.create(
        CreateTagParams(
            requester_role=auth.user.role,
            slug=payload.slug,
            name=payload.name,
            category=payload.category,
            description=payload.description,
        )
    )
    return TagResponse(**_tag_to_dict(tag))


@tags_router.get("/problems/{problem_id}", response_model=list[TagResponse])
def list_problem_tags(
    problem_id: int,
    service: TagService = Depends(get_tag_service),
):
    items = service.list_for_problem(problem_id)
    return [TagResponse(**_tag_to_dict(t)) for t in items]


@tags_router.post(
    "/problems/{problem_id}/attach",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def attach_tag(
    problem_id: int,
    payload: AttachTagRequest,
    auth: AuthContext = Depends(get_current_auth),
    service: TagService = Depends(get_tag_service),
):
    from app.services.community import AttachTagParams

    service.attach(
        AttachTagParams(
            problem_id=problem_id,
            tag_id=payload.tag_id,
            approved=payload.approved,
            requester_role=auth.user.role,
        )
    )
    return None


@tags_router.delete(
    "/problems/{problem_id}/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def detach_tag(
    problem_id: int,
    tag_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: TagService = Depends(get_tag_service),
):
    service.detach(problem_id, tag_id, auth.user.role)
    return None


# 辅助函数


def _detail_to_dict(detail) -> dict:
    return {
        "id": detail.id,
        "problem_id": detail.problem_id,
        "author_id": detail.author_id,
        "author_username": detail.author_username,
        "title": detail.title,
        "content": detail.content,
        "language": detail.language,
        "is_official": detail.is_official,
        "status": detail.status,
        "vote_count": detail.vote_count,
        "comment_count": detail.comment_count,
        "view_count": detail.view_count,
        "liked_by_me": detail.liked_by_me,
        "favorited_by_me": detail.favorited_by_me,
        "favorite_count": detail.favorite_count,
        "created_at": detail.created_at,
        "updated_at": detail.updated_at,
    }


def _tag_to_dict(tag) -> dict:
    return {
        "id": tag.id,
        "slug": tag.slug,
        "name": tag.name,
        "category": tag.category,
        "description": tag.description,
    }

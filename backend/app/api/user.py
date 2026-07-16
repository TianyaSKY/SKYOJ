"""用户 HTTP 接口。"""

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_user_service
from app.domain.user import UploadAvatarParams, UserProfile, UserSubmissionItem
from app.services.user_service import UserService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


def _profile_response(profile: UserProfile) -> dict:
    return {"id": profile.id, "username": profile.username, "role": profile.role, "avatar": profile.avatar}


def _submission_response(item: UserSubmissionItem) -> dict:
    return {
        "id": item.id, "problem_id": item.problem_id, "problem_title": item.problem_title,
        "status": item.status, "score": item.score, "language": item.language,
        "created_at": item.created_at.isoformat(), "exam_id": item.exam_id,
    }


@router.get("/all")
def get_all_users(
    auth: AuthContext = Depends(get_current_auth),
    service: UserService = Depends(get_user_service),
):
    return [_profile_response(user) for user in service.list_users(auth.user.role)]


@router.get("/{user_id}/profile")
def get_user_profile(user_id: int, service: UserService = Depends(get_user_service)):
    return _profile_response(service.get_profile(user_id))


@router.post("/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_auth),
    service: UserService = Depends(get_user_service),
):
    profile = service.upload_avatar(
        UploadAvatarParams(user_id=auth.user.id, filename=avatar.filename or "", content=await avatar.read())
    )
    return {"message": "Avatar uploaded successfully", "avatar": profile.avatar}


@router.get("/avatars/{filename}")
def get_avatar_file(filename: str, service: UserService = Depends(get_user_service)):
    return FileResponse(service.get_avatar_path(filename))


@router.get("/{user_id}/submissions")
def get_other_user_submissions(
    user_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: UserService = Depends(get_user_service),
):
    return [_submission_response(item) for item in service.list_submissions(user_id)]


@router.get("/submissions")
def get_user_submissions(
    auth: AuthContext = Depends(get_current_auth),
    service: UserService = Depends(get_user_service),
):
    return [_submission_response(item) for item in service.list_submissions(auth.user.id)]

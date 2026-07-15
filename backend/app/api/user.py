import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BACKEND_ROOT
from app.database import get_db
from app.models.submission import Submission
from app.models.user import User
from app.utils.auth_tools import AuthContext, get_current_auth
from app.utils.files import secure_filename

router = APIRouter()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _avatar_folder() -> str:
    return os.path.join(BACKEND_ROOT, "uploads", "avatars")


@router.get("/all")
def get_all_users(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "avatar": u.avatar,
        }
        for u in users
    ]


@router.get("/{user_id}/profile")
def get_user_profile(
    user_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"error": "Not found"})
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "avatar": user.avatar,
    }


@router.post("/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if not avatar.filename:
        raise HTTPException(status_code=400, detail={"error": "No selected file"})

    if not allowed_file(avatar.filename):
        raise HTTPException(status_code=400, detail={"error": "Invalid file type"})

    filename = secure_filename(avatar.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{ext}"

    upload_folder = _avatar_folder()
    os.makedirs(upload_folder, exist_ok=True)

    dest = os.path.join(upload_folder, new_filename)
    content = await avatar.read()
    with open(dest, "wb") as f:
        f.write(content)

    user = db.get(User, auth.user.id)
    user.avatar = f"/api/user/avatars/{new_filename}"
    db.commit()

    return {"message": "Avatar uploaded successfully", "avatar": user.avatar}


@router.get("/avatars/{filename}")
def get_avatar_file(filename: str):
    upload_folder = _avatar_folder()
    path = os.path.join(upload_folder, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail={"error": "File not found"})
    return FileResponse(path)


@router.get("/{user_id}/submissions")
def get_other_user_submissions(
    user_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    submissions = (
        db.query(Submission)
        .filter_by(user_id=user_id)
        .order_by(Submission.created_at.desc())
        .all()
    )

    result = []
    for s in submissions:
        result.append(
            {
                "id": s.id,
                "problem_id": s.problem_id,
                "problem_title": s.problem.title if s.problem else "Unknown",
                "status": s.status,
                "score": s.score,
                "language": s.language,
                "created_at": s.created_at.isoformat(),
                "exam_id": s.exam_id,
            }
        )
    return result


@router.get("/submissions")
def get_user_submissions(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    user = auth.user
    submissions = (
        db.query(Submission)
        .filter_by(user_id=user.id)
        .order_by(Submission.created_at.desc())
        .all()
    )

    result = []
    for s in submissions:
        result.append(
            {
                "id": s.id,
                "problem_id": s.problem_id,
                "problem_title": s.problem.title if s.problem else "Unknown",
                "status": s.status,
                "score": s.score,
                "language": s.language,
                "created_at": s.created_at.isoformat(),
                "exam_id": s.exam_id,
            }
        )
    return result

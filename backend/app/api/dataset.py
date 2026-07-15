import os
import threading
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import UPLOAD_FOLDER
from app.database import get_db
from app.models.dataset import Dataset
from app.utils.auth_tools import AuthContext, decode_auth_token, get_current_auth
from app.utils.files import secure_filename
from app.utils.pagination import paginate

router = APIRouter()

MAX_DATASET_SIZE = 500 * 1024 * 1024


def async_save_file(file_data, file_path, dataset_id):
    try:
        with open(file_path, "wb") as f:
            f.write(file_data)
    except Exception as e:
        print(f"Error in async_save_file: {e}")


@router.get("")
def get_datasets(
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Dataset).order_by(Dataset.id.desc())
    if page and page_size:
        datasets, total, _pages = paginate(query, page=page, per_page=page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "datasets": [d.to_dict() for d in datasets],
        }

    datasets = query.all()
    return [d.to_dict() for d in datasets]


@router.post("", status_code=202)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Permission denied. Only teachers can upload datasets."
            },
        )
    if not file.filename:
        raise HTTPException(status_code=400, detail={"error": "No selected file"})

    content = await file.read()
    size_bytes = len(content)
    if size_bytes > MAX_DATASET_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "error": f"File too large. Maximum size is {MAX_DATASET_SIZE // (1024 * 1024)}MB.You file size is {size_bytes // (1024 * 1024)}"
            },
        )

    filename = secure_filename(file.filename)
    upload_dir = os.path.join(UPLOAD_FOLDER, "datasets")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)

    if size_bytes < 1024:
        file_size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        file_size_str = f"{size_bytes / 1024:.2f} KB"
    else:
        file_size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

    dataset = Dataset(
        name=name,
        description=description,
        file_path=file_path,
        file_size=file_size_str,
        uploader_id=auth.user.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    thread = threading.Thread(
        target=async_save_file, args=(content, file_path, dataset.id)
    )
    thread.start()

    return {"message": "Upload started", "dataset": dataset.to_dict()}


@router.delete("/{id}")
def delete_dataset(
    id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Permission denied. Only teachers can delete datasets."
            },
        )

    dataset = db.get(Dataset, id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    if os.path.exists(dataset.file_path):
        try:
            os.remove(dataset.file_path)
        except Exception as e:
            print(f"Error deleting file {dataset.file_path}: {e}")

    db.delete(dataset)
    db.commit()
    return {"message": "Dataset deleted successfully"}


@router.get("/{id}/download")
def download_dataset(
    id: int,
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    auth_token = None
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization[7:].strip()
    else:
        auth_token = token

    if not auth_token:
        raise HTTPException(
            status_code=401, detail={"message": "Authentication required"}
        )

    try:
        decode_auth_token(auth_token)
    except Exception:
        raise HTTPException(
            status_code=401, detail={"message": "Invalid or expired token"}
        )

    dataset = db.get(Dataset, id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    if not os.path.isfile(dataset.file_path):
        raise HTTPException(status_code=404, detail={"error": "File not found"})

    return FileResponse(
        dataset.file_path,
        filename=os.path.basename(dataset.file_path),
        media_type="application/octet-stream",
    )

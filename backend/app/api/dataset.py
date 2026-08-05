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

from app.api.deps import get_dataset_service
from app.domain.dataset import PaginatedDatasets, UploadDatasetParams
from app.services.dataset_service import DatasetService
from app.utils.auth_tools import AuthContext, decode_auth_token, get_current_auth

router = APIRouter()


@router.get("")
def get_datasets(
    page: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    service: DatasetService = Depends(get_dataset_service),
):
    result = service.list_datasets(page=page, page_size=page_size)
    if isinstance(result, PaginatedDatasets):
        return {
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
            "datasets": [_dataset_to_response(dataset) for dataset in result.datasets],
        }
    return [_dataset_to_response(dataset) for dataset in result]


@router.post("", status_code=202)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    auth: AuthContext = Depends(get_current_auth),
    service: DatasetService = Depends(get_dataset_service),
):
    await file.seek(0)
    dataset = service.upload_dataset(
        UploadDatasetParams(
            requester_role=auth.user.role,
            uploader_id=auth.user.id,
            filename=file.filename or "",
            content=file.file,
            name=name,
            description=description,
        )
    )

    return {"message": "Upload started", "dataset": _dataset_to_response(dataset)}


@router.delete("/{id}")
def delete_dataset(
    id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: DatasetService = Depends(get_dataset_service),
):
    service.delete_dataset(auth.user.role, id)
    return {"message": "Dataset deleted successfully"}


@router.get("/{id}/download")
def download_dataset(
    id: int,
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
    service: DatasetService = Depends(get_dataset_service),
):
    auth_token = None
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization[7:].strip()
    else:
        auth_token = token

    if not auth_token:
        raise HTTPException(
            status_code=401, detail={"error": "Authentication required"}
        )

    try:
        decode_auth_token(auth_token)
    except Exception:
        raise HTTPException(
            status_code=401, detail={"error": "Invalid or expired token"}
        )

    dataset = service.download_dataset(id)

    return FileResponse(
        dataset.file_path,
        filename=dataset.filename,
        media_type="application/octet-stream",
    )


def _dataset_to_response(dataset) -> dict:
    """在 HTTP 边界组装数据集响应。"""
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "uploader": dataset.uploader,
        "file_size": dataset.file_size,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "download_url": f"/api/datasets/{dataset.id}/download",
        "status": dataset.status,
    }

"""系统设置 HTTP 接口。"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_system_service
from app.api.schemas.sys_dict import UpdateSysConfigBody
from app.database import get_db
from app.services.system_service import SystemService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.get("/info")
def get_sys_info(
    service: SystemService = Depends(get_system_service),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    include_llm_endpoint = False
    if authorization:
        try:
            auth = get_current_auth(authorization, db)
            include_llm_endpoint = auth.user.role == "teacher"
        except HTTPException:
            pass
    return service.get_config(include_llm_endpoint=include_llm_endpoint)


@router.put("/info")
def update_sys_info(body: UpdateSysConfigBody, auth: AuthContext = Depends(get_current_auth), service: SystemService = Depends(get_system_service)):
    updated, skipped = service.update_config(auth.user.role, body.root)
    return {"message": "System configuration updated successfully", "updated_keys": updated, "skipped_keys": skipped}


@router.delete("/info/{key}")
def delete_sys_info(key: str, auth: AuthContext = Depends(get_current_auth), service: SystemService = Depends(get_system_service)):
    service.delete_config(auth.user.role, key)
    return {"message": f"Key '{key}' deleted successfully"}


@router.get("/statistics")
def get_statistics(auth: AuthContext = Depends(get_current_auth), service: SystemService = Depends(get_system_service)):
    return service.statistics(auth.user.role)

"""系统设置 HTTP 接口。"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_system_service
from app.api.schemas.common import MessageResponse
from app.api.schemas.sys_dict import (
    SystemConfigResponse,
    SystemStatisticsResponse,
    UpdateSysConfigBody,
    UpdateSysConfigResponse,
)
from app.persistence.database import get_db
from app.services.system import SystemService, UpdateSystemConfigParams

router = APIRouter()


@router.get("/info", response_model=SystemConfigResponse)
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
    return service.get_config(include_llm_endpoint=include_llm_endpoint).payload


@router.put("/info", response_model=UpdateSysConfigResponse)
def update_sys_info(
    body: UpdateSysConfigBody,
    auth: AuthContext = Depends(get_current_auth),
    service: SystemService = Depends(get_system_service),
):
    result = service.update_config(auth.user.role, UpdateSystemConfigParams(body.root))
    return {
        "message": "System configuration updated successfully",
        "updated_keys": result.updated_keys,
        "skipped_keys": result.skipped_keys,
    }


@router.delete("/info/{key}", response_model=MessageResponse)
def delete_sys_info(
    key: str,
    auth: AuthContext = Depends(get_current_auth),
    service: SystemService = Depends(get_system_service),
):
    service.delete_config(auth.user.role, key)
    return {"message": f"Key '{key}' deleted successfully"}


@router.get("/statistics", response_model=SystemStatisticsResponse)
def get_statistics(
    auth: AuthContext = Depends(get_current_auth),
    service: SystemService = Depends(get_system_service),
):
    return service.statistics(auth.user.role)

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_auth_service
from app.api.schemas.auth import LoginBody, LoginResponse, RegisterBody
from app.api.schemas.common import MessageResponse
from app.domain.auth import LoginParams, RegisterParams
from app.middleware.rate_limit import client_ip_from_request, enforce
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", status_code=201, response_model=MessageResponse)
def register(
    body: RegisterBody,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = client_ip_from_request(request)
    enforce(f"register:{ip}", limit=3, window_seconds=60)
    service.register(
        RegisterParams(
            username=body.username,
            password=body.password,
        )
    )
    return {"message": "User registered successfully"}


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginBody,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = client_ip_from_request(request)
    enforce(f"login:{ip}", limit=5, window_seconds=60)
    result = service.login(LoginParams(username=body.username, password=body.password))
    return {
        "message": "Login successful",
        "token": result.token,
        "user": {
            "id": result.user.id,
            "username": result.user.username,
            "role": result.user.role,
        },
    }

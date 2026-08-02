from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service
from app.api.schemas.auth import LoginBody, RegisterBody
from app.domain.auth import LoginParams, RegisterParams
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", status_code=201)
def register(
    body: RegisterBody,
    service: AuthService = Depends(get_auth_service),
):
    service.register(
        RegisterParams(
            username=body.username,
            password=body.password,
        )
    )
    return {"message": "User registered successfully"}


@router.post("/login")
def login(body: LoginBody, service: AuthService = Depends(get_auth_service)):
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

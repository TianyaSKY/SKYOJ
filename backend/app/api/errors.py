"""统一业务异常与 HTTP 错误响应。"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.error_codes import (
    AUTH_REQUIRED,
    BUSINESS_ERROR,
    EXTERNAL_SERVICE_ERROR,
    INVALID_STATE,
    PERMISSION_DENIED,
    RATE_LIMIT_EXCEEDED,
    RESOURCE_NOT_FOUND,
    status_to_code,
)
from app.core.errors import (
    AuthenticationError,
    BusinessError,
    ExternalServiceError,
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.middleware.rate_limit import RateLimitExceeded


def register_exception_handlers(application: FastAPI) -> None:
    def _envelope(status_code: int, code: str, **fields) -> dict:
        """构造统一的错误响应体：``{"code": ..., "error": ..., ...}``。"""
        payload = {"code": code, **fields}
        return payload

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """保留结构化字段错误，并统一提供可供客户端判断的错误码。"""
        return JSONResponse(
            status_code=422,
            content=_envelope(422, status_to_code(422), detail=jsonable_encoder(exc.errors())),
        )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Preserve Flask-style JSON bodies when detail is a dict, 同时补 code
        code = status_to_code(exc.status_code)
        if isinstance(exc.detail, dict):
            body = dict(exc.detail)
            body.setdefault("code", code)
            return JSONResponse(status_code=exc.status_code, content=body)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.status_code, code, detail=str(exc.detail)),
        )

    @application.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request, exc: ResourceNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_envelope(404, RESOURCE_NOT_FOUND, error=str(exc)),
        )

    @application.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(
        request: Request, exc: PermissionDeniedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content=_envelope(403, PERMISSION_DENIED, error=str(exc)),
        )

    @application.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content=_envelope(401, AUTH_REQUIRED, error=str(exc)),
        )

    @application.exception_handler(InvalidStateError)
    async def invalid_state_handler(
        request: Request, exc: InvalidStateError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_envelope(400, INVALID_STATE, error=str(exc)),
        )

    @application.exception_handler(ExternalServiceError)
    async def external_service_error_handler(
        request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content=_envelope(502, EXTERNAL_SERVICE_ERROR, error=str(exc)),
        )

    @application.exception_handler(BusinessError)
    async def business_error_handler(
        request: Request, exc: BusinessError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_envelope(400, BUSINESS_ERROR, error=str(exc)),
        )

    @application.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=_envelope(
                429,
                RATE_LIMIT_EXCEEDED,
                error="请求过于频繁，请稍后再试",
                retry_after=exc.retry_after,
            ),
            headers={"Retry-After": str(exc.retry_after)},
        )

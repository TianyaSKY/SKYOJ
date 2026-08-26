import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import OperationalError

from app.api import (
    auth,
    dataset,
    debug,
    exam,
    llm,
    plagiarism,
    problem,
    problem_community,
    search,
    submission,
    sys_dict,
    user,
)
from app.database import SessionLocal, create_tables
from app.domain.errors import (
    AuthenticationError,
    BusinessError,
    ExternalServiceError,
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitExceeded
from app.models.sysdict import SysDict
from app.utils.error_codes import (
    AUTH_REQUIRED,
    BUSINESS_ERROR,
    EXTERNAL_SERVICE_ERROR,
    INVALID_STATE,
    PERMISSION_DENIED,
    RATE_LIMIT_EXCEEDED,
    RESOURCE_NOT_FOUND,
    status_to_code,
)
from app.utils.sys_dict import sys_dict_kv


def init_db():
    """尝试连接数据库并创建表，带有重试机制"""
    retries = 5
    while retries > 0:
        try:
            create_tables()
            logger.success("数据库连接成功，数据表已创建")

            db = SessionLocal()
            try:
                if db.query(SysDict).count() == 0:
                    for key, val in sys_dict_kv.items():
                        db.add(SysDict(key=key, val=str(val)))
                    db.commit()
                    logger.success("系统字典已根据默认配置完成初始化")
            finally:
                db.close()
            return
        except OperationalError as exc:
            retries -= 1
            logger.warning(
                "数据库暂不可用，准备重试，第 {} 次/共 5 次，原因：{}",
                5 - retries,
                exc,
            )
            time.sleep(3)
        except Exception as exc:
            retries -= 1
            logger.exception(
                "数据库初始化失败，准备重试，第 {} 次/共 5 次，原因：{}",
                5 - retries,
                exc,
            )
            time.sleep(3)
    logger.error("数据库多次连接失败，应用将以降级状态继续启动")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI 推荐的 lifespan 处理器，替换弃用的 on_event。

    仅负责启动期的数据库初始化与字典种子；无关闭钩子。
    """
    init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="SKYOJ Backend",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    def _envelope(status_code: int, code: str, **fields) -> dict:
        """构造统一的错误响应体：``{"code": ..., "error": ..., ...}``。"""
        payload = {"code": code, **fields}
        return payload

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

    application.add_middleware(AuditMiddleware)

    @application.get("/")
    def hello():
        return {"status": "SKYOJ Backend is ready!"}

    @application.get("/healthz")
    def healthz():
        return {"status": "ok"}

    application.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    application.include_router(problem.router, prefix="/api/problems", tags=["problems"])
    application.include_router(
        submission.router, prefix="/api/submissions", tags=["submissions"]
    )
    application.include_router(debug.router, prefix="/api/debug", tags=["debug"])
    application.include_router(user.router, prefix="/api/user", tags=["user"])
    application.include_router(
        dataset.router, prefix="/api/datasets", tags=["datasets"]
    )
    application.include_router(sys_dict.router, prefix="/api/sys", tags=["sys"])
    application.include_router(exam.router, prefix="/api/exams", tags=["exams"])
    application.include_router(llm.router, prefix="/api/llm", tags=["llm"])
    application.include_router(search.router, prefix="/api/search", tags=["search"])
    application.include_router(plagiarism.router, prefix="/api/plagiarism", tags=["plagiarism"])
    application.include_router(problem_community.router, prefix="/api", tags=["community"])
    application.include_router(problem_community.tags_router, prefix="/api", tags=["community"])

    return application


app = create_app()

import threading
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import OperationalError

from app.api import (
    auth,
    dataset,
    exam,
    llm,
    plagiarism,
    problem,
    search,
    submission,
    sys_dict,
    user,
)
from app.database import SessionLocal, create_tables
from app.domain.errors import (
    AuthenticationError,
    BusinessError,
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.models.sysdict import SysDict
from app.utils.feature_flags import ENABLE_PLAGIARISM, ENABLE_SEMANTIC_SEARCH
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


def init_services():
    """初始化搜索索引和查重模型"""
    if not (ENABLE_PLAGIARISM or ENABLE_SEMANTIC_SEARCH):
        logger.info(
            "搜索和查重服务已由功能开关禁用，跳过初始化"
        )
        return

    logger.info("开始初始化搜索索引与查重模型")
    try:
        if ENABLE_PLAGIARISM:
            from app.services.plagiarism_service import plagiarism_service

            plagiarism_service._ensure_model_loaded()

        if ENABLE_SEMANTIC_SEARCH:
            from app.services.search_service import search_service

            search_service.rebuild_index()

        logger.success("搜索索引与查重模型初始化完成")
    except Exception:
        logger.exception("搜索索引或查重模型初始化失败")


def create_app() -> FastAPI:
    application = FastAPI(title="SKYOJ Backend", docs_url="/docs", redoc_url="/redoc")

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Preserve Flask-style JSON bodies when detail is a dict
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail}
        )

    @application.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request, exc: ResourceNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @application.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(
        request: Request, exc: PermissionDeniedError
    ) -> JSONResponse:
        return JSONResponse(status_code=403, content={"error": str(exc)})

    @application.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"error": str(exc)})

    @application.exception_handler(InvalidStateError)
    async def invalid_state_handler(
        request: Request, exc: InvalidStateError
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @application.exception_handler(BusinessError)
    async def business_error_handler(
        request: Request, exc: BusinessError
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @application.get("/")
    def hello():
        return {"status": "SKYOJ Backend is ready!"}

    application.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    application.include_router(problem.router, prefix="/api/problems", tags=["problems"])
    application.include_router(
        submission.router, prefix="/api/submissions", tags=["submissions"]
    )
    application.include_router(user.router, prefix="/api/user", tags=["user"])
    application.include_router(
        dataset.router, prefix="/api/datasets", tags=["datasets"]
    )
    application.include_router(sys_dict.router, prefix="/api/sys", tags=["sys"])
    application.include_router(exam.router, prefix="/api/exams", tags=["exams"])
    application.include_router(llm.router, prefix="/api/llm", tags=["llm"])
    application.include_router(search.router, prefix="/api/search", tags=["search"])
    application.include_router(
        plagiarism.router, prefix="/api/plagiarism", tags=["plagiarism"]
    )

    @application.on_event("startup")
    def on_startup():
        init_db()
        threading.Thread(target=init_services, daemon=True).start()

    return application


app = create_app()

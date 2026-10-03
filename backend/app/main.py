"""应用工厂与生命周期入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.router import register_routes
from app.middleware.audit import AuditMiddleware
from app.middleware.metrics import register_metrics
from app.persistence.bootstrap import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动前检查数据库并创建缺失表。"""
    init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="SKYOJ Backend",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    register_metrics(application)
    register_exception_handlers(application)
    application.add_middleware(AuditMiddleware)
    register_routes(application)
    return application


app = create_app()

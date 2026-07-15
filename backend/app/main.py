import threading
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
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
from app.models.sysdict import SysDict
from app.utils.feature_flags import ENABLE_PLAGIARISM, ENABLE_SEMANTIC_SEARCH
from app.utils.sys_dict import sys_dict_kv


def init_db():
    """尝试连接数据库并创建表，带有重试机制"""
    retries = 5
    while retries > 0:
        try:
            create_tables()
            print("Successfully connected to MySQL and created tables!")

            db = SessionLocal()
            try:
                if db.query(SysDict).count() == 0:
                    for key, val in sys_dict_kv.items():
                        db.add(SysDict(key=key, val=str(val)))
                    db.commit()
                    print("Initialized SysDict from sys_dict_kv.")
            finally:
                db.close()
            return
        except OperationalError:
            retries -= 1
            print(f"Waiting for MySQL... ({5 - retries}/5)")
            time.sleep(3)
        except Exception as e:
            retries -= 1
            print(f"DB init error: {e} ({5 - retries}/5)")
            time.sleep(3)
    print("Could not connect to MySQL after several retries.")


def init_services():
    """初始化搜索索引和查重模型"""
    if not (ENABLE_PLAGIARISM or ENABLE_SEMANTIC_SEARCH):
        print(
            "Search and plagiarism services are disabled by feature flags. Skipping init."
        )
        return

    print("Initializing services (Search Index & Plagiarism Model)...")
    try:
        if ENABLE_PLAGIARISM:
            from app.services.plagiarism_service import plagiarism_service

            plagiarism_service._ensure_model_loaded()

        if ENABLE_SEMANTIC_SEARCH:
            from app.services.search_service import search_service

            search_service.rebuild_index()

        print("Services initialized successfully.")
    except Exception as e:
        print(f"Error initializing services: {e}")


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

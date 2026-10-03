"""集中注册业务路由和健康检查。"""

from fastapi import FastAPI

from app.api import (
    admin_analytics,
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
    wrong_book,
)


def register_routes(application: FastAPI) -> None:
    @application.get("/")
    def hello():
        return {"status": "SKYOJ Backend is ready!"}

    @application.get("/healthz")
    def healthz():
        return {"status": "ok"}

    application.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    application.include_router(
        problem.router, prefix="/api/problems", tags=["problems"]
    )
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
    application.include_router(
        plagiarism.router, prefix="/api/plagiarism", tags=["plagiarism"]
    )
    application.include_router(
        problem_community.router, prefix="/api", tags=["community"]
    )
    application.include_router(
        problem_community.tags_router, prefix="/api", tags=["community"]
    )
    application.include_router(wrong_book.router, prefix="/api", tags=["wrong_book"])
    application.include_router(admin_analytics.router, prefix="/api", tags=["admin"])

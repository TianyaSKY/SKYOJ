"""审计中间件：自动记录所有写操作（POST/PUT/DELETE/PATCH）的请求和响应摘要。"""

import json
from datetime import datetime

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.database import SessionLocal
from app.models.audit_log import AuditLog


_AUDITED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def _resolve_user_id_from_state(request: Request) -> int | None:
    """从 FastAPI request.state 中提取已认证用户 ID（如有）。

    AuthContext 在 get_current_auth 中注入到 request.state.auth_context。
    """
    auth_ctx = getattr(request.state, "auth_context", None)
    if auth_ctx is None:
        return None
    user = getattr(auth_ctx, "user", None)
    return getattr(user, "id", None) if user else None


def _summarize_payload(payload: bytes, content_type: str) -> str | None:
    """提取请求体摘要，避免直接存储大字段或敏感信息。"""
    if not payload:
        return None
    if "multipart/form-data" in content_type:
        return "<multipart>"
    try:
        text = payload.decode("utf-8")
        if len(text) > 1024:
            return text[:1024] + "..."
        return text
    except UnicodeDecodeError:
        return "<binary>"


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.method not in _AUDITED_METHODS:
            return await call_next(request)

        body = await request.body()

        response = await call_next(request)

        try:
            await self._write_log(request, response, body)
        except Exception as exc:
            logger.warning("审计日志写入失败 path={} error={}", request.url.path, exc)

        return response

    async def _write_log(self, request: Request, response, body: bytes) -> None:
        db = SessionLocal()
        try:
            entry = AuditLog(
                user_id=_resolve_user_id_from_state(request),
                action=f"{request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                ip=request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or (request.client.host if request.client else None),
                user_agent=request.headers.get("User-Agent", "")[:255] or None,
                payload_summary=_summarize_payload(body, request.headers.get("content-type", "")),
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()

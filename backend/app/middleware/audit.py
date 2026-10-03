"""审计中间件：自动记录所有写操作（POST/PUT/DELETE/PATCH）的请求和响应摘要。"""

import json
from urllib.parse import parse_qsl, urlencode

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.persistence.database import SessionLocal
from app.persistence.system import AuditLog


_AUDITED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
_REDACTED = "<redacted>"
_SENSITIVE_KEYS = {
    "password", "passwordhash", "passwd", "token", "accesstoken", "refreshtoken",
    "apikey", "secret", "secretkey", "clientsecret", "authorization", "cookie", "setcookie",
}


def _is_sensitive_key(key: str) -> bool:
    """统一大小写和命名分隔符，识别常见凭据字段。"""
    normalized = "".join(char for char in key.casefold() if char.isalnum())
    return normalized in _SENSITIVE_KEYS or normalized.endswith(
        ("password", "apikey", "secretkey", "accesstoken", "refreshtoken")
    )


def _redact_payload(value: object) -> object:
    """递归遮蔽结构化请求中的凭据字段，保留普通业务上下文。"""
    if isinstance(value, dict):
        return {
            key: _REDACTED if _is_sensitive_key(key) else _redact_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    return value


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
    media_type = content_type.split(";", 1)[0].strip().casefold()
    if media_type == "multipart/form-data":
        return "<multipart>"
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return "<binary>"
    if media_type == "application/x-www-form-urlencoded":
        text = urlencode([
            (key, _REDACTED if _is_sensitive_key(key) else value)
            for key, value in parse_qsl(text, keep_blank_values=True)
        ])
    elif not media_type or media_type == "application/json" or media_type.endswith("+json"):
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, (dict, list)):
                return "<json>"
            text = json.dumps(_redact_payload(parsed), ensure_ascii=False)
        except (ValueError, RecursionError):
            return "<invalid-json>"
    else:
        return "<text>"
    # 完成遮蔽后再截断，避免凭据被原样写入摘要前段。
    return text[:1024] + "..." if len(text) > 1024 else text


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

"""统一错误码：HTTP 状态码 + 业务错误名 → 机器可读 code 字符串。

前端 ``utils/request.js`` 通过 ``error.code`` 区分业务错误，触发登录失效弹窗
等行为。后端 ``main.py`` 的异常处理器统一在此映射。

新错误码时按 <域>_<动作>_<结果> 命名，例如：
- ``AUTH_TOKEN_EXPIRED`` 登录令牌过期
- ``EXAM_NOT_IN_PROGRESS`` 考试未在进行中
"""

from __future__ import annotations

from typing import Optional

# 认证域
AUTH_REQUIRED = "AUTH_REQUIRED"
AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"

# 业务域（按异常类型映射）
RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
PERMISSION_DENIED = "PERMISSION_DENIED"
INVALID_STATE = "INVALID_STATE"
EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
BUSINESS_ERROR = "BUSINESS_ERROR"
RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

# HTTP 状态码兜底
HTTP_BAD_REQUEST = "HTTP_BAD_REQUEST"
HTTP_NOT_FOUND = "HTTP_NOT_FOUND"
HTTP_CONFLICT = "HTTP_CONFLICT"
HTTP_INTERNAL = "HTTP_INTERNAL"


_STATUS_TO_CODE: dict[int, str] = {
    400: HTTP_BAD_REQUEST,
    401: AUTH_REQUIRED,
    403: PERMISSION_DENIED,
    404: HTTP_NOT_FOUND,
    409: HTTP_CONFLICT,
    429: RATE_LIMIT_EXCEEDED,
    500: HTTP_INTERNAL,
    502: EXTERNAL_SERVICE_ERROR,
}


def status_to_code(status_code: int) -> str:
    """HTTP 状态码 → 错误码字符串。"""
    return _STATUS_TO_CODE.get(status_code, f"HTTP_{status_code}")


__all__ = [
    "AUTH_INVALID_TOKEN",
    "AUTH_REQUIRED",
    "AUTH_TOKEN_EXPIRED",
    "BUSINESS_ERROR",
    "EXTERNAL_SERVICE_ERROR",
    "HTTP_BAD_REQUEST",
    "HTTP_CONFLICT",
    "HTTP_INTERNAL",
    "HTTP_NOT_FOUND",
    "INVALID_STATE",
    "PERMISSION_DENIED",
    "RATE_LIMIT_EXCEEDED",
    "RESOURCE_NOT_FOUND",
    "status_to_code",
]

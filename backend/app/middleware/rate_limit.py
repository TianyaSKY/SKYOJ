"""基于 Redis 的简易限流器（固定窗口算法）。

每个 (key, window) 维护一个计数器，超过上限时拒绝请求。
Redis 不可用时放行（fail-open），避免影响主流程。
"""

import os
import time
from typing import Optional

import redis
from loguru import logger

_REDIS_URL = os.getenv("REDIS_URL") or ""
_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    global _client
    if _client is None and _REDIS_URL:
        _client = redis.from_url(_REDIS_URL, decode_responses=True)
    return _client


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry after {retry_after}s")


def check_rate_limit(
    key: str, limit: int, window_seconds: int, *, now: int | None = None
) -> bool:
    """检查 key 在当前窗口内是否超过限制。

    返回 True 表示允许（计数未超），False 表示拒绝。
    """
    try:
        client = _get_client()
        if client is None:
            return True

        if now is None:
            now = int(time.time())
        bucket = now // window_seconds
        redis_key = f"skyoj:ratelimit:{key}:{bucket}"
        pipe = client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window_seconds + 5)
        count, _ = pipe.execute()
        return int(count) <= limit
    except Exception as exc:
        logger.warning("限流检查失败，降级放行 key={} error={}", key, exc)
        return True


def enforce(key: str, limit: int, window_seconds: int) -> None:
    """限流检查，超限时抛 RateLimitExceeded。"""
    now = int(time.time())
    if not check_rate_limit(key, limit, window_seconds, now=now):
        # Redis 返回时可能已跨窗；等待时间仍以实际计数的窗口为准。
        window_end = (now // window_seconds + 1) * window_seconds
        retry_after = max(1, window_end - int(time.time()))
        raise RateLimitExceeded(retry_after=retry_after)


def client_ip_from_request(request) -> str:
    """从 FastAPI Request 解析客户端 IP（优先 X-Forwarded-For）。"""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

"""题目详情 Redis 缓存。

失效策略：
- 读取时按 key 命中；miss 时回源计算，写入缓存
- 写入缓存时设置 TTL=300s（题目详情改动频率低，缓存窗口长更有效）
- update_problem / delete_problem 主动删除缓存
"""

import json
import os
from typing import Any, Optional

import redis

_REDIS_URL = os.getenv("REDIS_URL") or ""
_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    global _client
    if _client is None and _REDIS_URL:
        _client = redis.from_url(_REDIS_URL, decode_responses=True)
    return _client


DETAIL_KEY = "skyoj:problem:{problem_id}:detail"
DETAIL_TTL_SECONDS = 300


def get_detail_cache(problem_id: int) -> Optional[dict[str, Any]]:
    """读取题目详情缓存，未命中返回 None。"""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(DETAIL_KEY.format(problem_id=problem_id))
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def set_detail_cache(problem_id: int, payload: dict[str, Any]) -> None:
    """写入题目详情缓存。"""
    client = _get_client()
    if client is None:
        return
    try:
        client.set(
            DETAIL_KEY.format(problem_id=problem_id),
            json.dumps(payload, ensure_ascii=False, default=str),
            ex=DETAIL_TTL_SECONDS,
        )
    except Exception:
        return


def invalidate_detail_cache(problem_id: int) -> None:
    """题目被更新或删除时主动失效缓存。Redis 不可用时静默。"""
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(DETAIL_KEY.format(problem_id=problem_id))
    except Exception:
        return

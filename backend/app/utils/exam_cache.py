"""考试缓存：排行榜 JSON 序列化结果缓存到 Redis。

失效策略：
- 读取时按 key 命中；miss 时回源计算，写入缓存
- 写入缓存时设置 TTL=60s
- 判题完成（提交判题回调）时主动删除 exam:{id}:rank 缓存
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


RANK_KEY = "skyoj:exam:{exam_id}:rank"
RANK_TTL_SECONDS = 60


def get_rank_cache(exam_id: int) -> Optional[dict[str, Any]]:
    """读取排行榜缓存，未命中返回 None。"""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(RANK_KEY.format(exam_id=exam_id))
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def set_rank_cache(exam_id: int, payload: dict[str, Any]) -> None:
    """写入排行榜缓存。"""
    client = _get_client()
    if client is None:
        return
    try:
        client.set(
            RANK_KEY.format(exam_id=exam_id),
            json.dumps(payload, ensure_ascii=False, default=str),
            ex=RANK_TTL_SECONDS,
        )
    except Exception:
        return


def invalidate_rank_cache(exam_id: int) -> None:
    """判题完成时主动失效。Redis 不可用时静默。"""
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(RANK_KEY.format(exam_id=exam_id))
    except Exception:
        return

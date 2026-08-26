"""实时推送工具：基于 Redis pub/sub 的跨进程实时通知。

通知通道：submission:{submission_id}
消息格式（JSON）：
  {"status": "Accepted", "score": 100.0, "output_log": "..."}
"""

import json
import os
from typing import Optional

import redis

_REDIS_URL: Optional[str] = None
_PUBSUB_CHANNEL_PREFIX = "skyoj:submission:"


def _get_redis_url() -> Optional[str]:
    global _REDIS_URL
    if _REDIS_URL is None:
        _REDIS_URL = os.getenv("REDIS_URL") or os.getenv("REDIS_URL", "")
    return _REDIS_URL if _REDIS_URL else None


def _redis_client():
    url = _get_redis_url()
    if url:
        return redis.from_url(url, decode_responses=True)
    return None


def publish_submission_result(submission_id: int, status: str, score: float, output_log: str) -> bool:
    """在判题 Worker 中调用：将结果发布到 Redis channel，供 WebSocket 消费。

    即使 Redis 不可用也静默失败，不影响判辖市主流程。
    """
    try:
        client = _redis_client()
        if client is None:
            return False
        channel = f"{_PUBSUB_CHANNEL_PREFIX}{submission_id}"
        payload = json.dumps({
            "submission_id": submission_id,
            "status": status,
            "score": score,
            "output_log": output_log or "",
        }, ensure_ascii=False)
        client.publish(channel, payload)
        return True
    except Exception:
        return False

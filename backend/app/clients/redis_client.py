"""共享 Redis 连接及 JSON 缓存/通知操作；不可用时记录降级原因。"""

import json
import os
from typing import Any

import redis
from loguru import logger


class RedisClient:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    def get_client(self) -> redis.Redis | None:
        url = os.getenv("REDIS_URL") or ""
        if self._client is None and url:
            self._client = redis.from_url(url, decode_responses=True)
        return self._client

    def get_json(self, key: str) -> dict[str, Any] | None:
        try:
            client = self.get_client()
            if client is None:
                return None
            raw = client.get(key)
            if raw is None:
                return None
            value = json.loads(raw)
            if not isinstance(value, dict):
                logger.warning("Redis 缓存结构无效 key={}", key)
                return None
            return value
        except (redis.RedisError, TypeError, ValueError) as exc:
            logger.warning("Redis 缓存读取降级 key={} error={}", key, exc)
            return None

    def set_json(self, key: str, payload: dict[str, Any], *, ttl: int) -> None:
        try:
            client = self.get_client()
            if client is not None:
                client.set(
                    key, json.dumps(payload, ensure_ascii=False, default=str), ex=ttl
                )
        except (redis.RedisError, TypeError, ValueError) as exc:
            logger.warning("Redis 缓存写入降级 key={} error={}", key, exc)

    def delete(self, key: str) -> None:
        try:
            client = self.get_client()
            if client is not None:
                client.delete(key)
        except redis.RedisError as exc:
            logger.warning("Redis 缓存失效降级 key={} error={}", key, exc)

    def publish(self, channel: str, payload: dict[str, Any]) -> bool:
        try:
            client = self.get_client()
            if client is None:
                return False
            client.publish(channel, json.dumps(payload, ensure_ascii=False))
            return True
        except (redis.RedisError, TypeError, ValueError) as exc:
            logger.warning("Redis 通知发布降级 channel={} error={}", channel, exc)
            return False


redis_client = RedisClient()

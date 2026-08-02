"""时间工具。"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """返回不带时区信息的 UTC 时间，兼容现有数据库字段。"""
    return datetime.now(UTC).replace(tzinfo=None)


__all__ = ["utcnow"]

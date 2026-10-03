"""时间工具。"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """返回不带时区信息的 UTC 时间，兼容现有数据库字段。"""
    return datetime.now(UTC).replace(tzinfo=None)


def to_utc_naive(value: datetime) -> datetime:
    """将带时区时间转换为数据库使用的 UTC；无时区时间沿用现有 UTC 约定。"""
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


__all__ = ["utcnow", "to_utc_naive"]

"""判题时限换算回归测试。"""

from app.services.sandbox_runner import time_limit_seconds


def test_time_limit_seconds_converts_milliseconds() -> None:
    assert time_limit_seconds(1000) == 1
    assert time_limit_seconds(1500) == 2
    assert time_limit_seconds(30000) == 30
    assert time_limit_seconds(50) == 1
    assert time_limit_seconds(None) == 1
    assert time_limit_seconds("bad") == 1

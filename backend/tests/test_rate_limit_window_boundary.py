"""Retry-After 使用实际计数的窗口，跨窗口响应不得变成零、负数或新一整窗。"""

from unittest.mock import MagicMock

import pytest

from app.middleware import rate_limit


@pytest.mark.parametrize('started,finished,expected', [
    (120, 121, 59), (179, 180, 1), (119, 180, 1), (120, 240, 1),
])
def test_retry_after_matches_counted_window(monkeypatch, started, finished, expected):
    client = MagicMock()
    client.pipeline.return_value.execute.return_value = (11, True)
    monkeypatch.setattr(rate_limit, '_get_client', lambda: client)
    monkeypatch.setattr(rate_limit.time, 'time', MagicMock(side_effect=[started, finished, finished]))
    with pytest.raises(rate_limit.RateLimitExceeded) as result:
        rate_limit.enforce('submit:1', 10, 60)
    assert result.value.retry_after == expected
    client.pipeline.return_value.incr.assert_called_once_with(f'skyoj:ratelimit:submit:1:{started // 60}')


def test_first_request_in_new_window_is_allowed_without_retry_calculation(monkeypatch):
    client = MagicMock()
    client.pipeline.return_value.execute.return_value = (1, True)
    monkeypatch.setattr(rate_limit, '_get_client', lambda: client)
    clock = MagicMock(return_value=180)
    monkeypatch.setattr(rate_limit.time, 'time', clock)
    rate_limit.enforce('submit:1', 10, 60)
    client.pipeline.return_value.incr.assert_called_once_with('skyoj:ratelimit:submit:1:3')
    clock.assert_called_once()

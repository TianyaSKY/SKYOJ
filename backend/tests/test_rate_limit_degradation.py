"""Redis 限流故障必须按既有约定放行，并提供诊断日志。"""

from unittest.mock import MagicMock

import pytest
import redis

from app.middleware import rate_limit


@pytest.mark.parametrize('stage', ['initialize', 'pipeline', 'execute', 'decode_count'])
def test_all_redis_failure_stages_allow_request_and_log_context(monkeypatch, stage):
    client = MagicMock()
    pipe = client.pipeline.return_value
    pipe.execute.return_value = (1, True)
    errors = {
        'initialize': ValueError('invalid Redis URL scheme'),
        'pipeline': redis.ConnectionError('connection unavailable'),
        'execute': redis.TimeoutError('request timed out'),
        'decode_count': ValueError('invalid literal'),
    }
    if stage == 'initialize':
        monkeypatch.setattr(rate_limit, '_get_client', MagicMock(side_effect=errors[stage]))
    else:
        monkeypatch.setattr(rate_limit, '_get_client', lambda: client)
        if stage == 'pipeline':
            client.pipeline.side_effect = errors[stage]
        elif stage == 'execute':
            pipe.execute.side_effect = errors[stage]
        else:
            pipe.execute.return_value = ('invalid', True)
    logger = MagicMock()
    monkeypatch.setattr(rate_limit, 'logger', logger)
    rate_limit.enforce('submit:7', 10, 60)
    logger.warning.assert_called_once()
    assert logger.warning.call_args.args[1] == 'submit:7'
    assert isinstance(logger.warning.call_args.args[2], Exception)


def test_unconfigured_redis_allows_without_failure_warning(monkeypatch):
    monkeypatch.setattr(rate_limit, '_get_client', lambda: None)
    logger = MagicMock()
    monkeypatch.setattr(rate_limit, 'logger', logger)
    assert rate_limit.check_rate_limit('submit:7', 10, 60)
    logger.warning.assert_not_called()


def test_redis_recovers_after_failure_and_resumes_enforcing_quota(monkeypatch):
    client = MagicMock()
    client.pipeline.return_value.execute.side_effect = [redis.ConnectionError('down'), (11, True)]
    monkeypatch.setattr(rate_limit, '_get_client', lambda: client)
    logger = MagicMock()
    monkeypatch.setattr(rate_limit, 'logger', logger)
    rate_limit.enforce('submit:7', 10, 60)
    with pytest.raises(rate_limit.RateLimitExceeded):
        rate_limit.enforce('submit:7', 10, 60)
    logger.warning.assert_called_once()

"""调试与正式提交共用用户配额，超限不创建任务，窗口和用户相互隔离。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_debug_service, get_submission_service
from app.middleware import rate_limit
from app.services.auth import AuthUserInfo


class MemoryRateCounter:
    """记录 API 限流器发出的 Redis 计数事务，按完整窗口键存储。"""

    def __init__(self):
        self.counts = {}

    def pipeline(self):
        owner = self

        class Pipeline:
            def incr(self, key):
                self.key = key

            def expire(self, key, seconds):
                pass

            def execute(self):
                owner.counts[self.key] = owner.counts.get(self.key, 0) + 1
                return owner.counts[self.key], True

        return Pipeline()


@pytest.mark.parametrize('first', ['debug', 'submit'])
def test_debug_and_submit_share_quota_but_not_users_or_windows(client, monkeypatch, first):
    counter = MemoryRateCounter()
    now = [120]
    user_id = [1]
    monkeypatch.setattr(rate_limit, '_get_client', lambda: counter)
    monkeypatch.setattr(rate_limit.time, 'time', lambda: now[0])
    client.app.dependency_overrides[get_current_auth] = lambda: AuthContext(
        user=AuthUserInfo(id=user_id[0], username='student', role='student'),
    )
    service = MagicMock()
    service.submit.return_value = SimpleNamespace(submission_id=17, status='Pending', exam_id=None)
    service.create.return_value = SimpleNamespace(debug_run_id=18, status='Pending', exam_id=None)
    client.app.dependency_overrides[get_submission_service] = lambda: service
    client.app.dependency_overrides[get_debug_service] = lambda: service
    endpoints = ['/api/debug', '/api/submissions/submit']
    if first == 'submit':
        endpoints.reverse()
    payload = {'problem_id': 1, 'language': 'python', 'code': 'print(1)'}
    for index in range(10):
        assert client.post(endpoints[index % 2], json=payload).status_code == 202
    assert service.create.call_count == 5
    assert service.submit.call_count == 5
    for endpoint in endpoints:
        response = client.post(endpoint, json=payload)
        assert response.status_code == 429
        assert response.json()['code'] == 'RATE_LIMIT_EXCEEDED'
        assert response.json()['retry_after'] == 60
        assert response.headers['Retry-After'] == '60'
    assert service.create.call_count == 5
    assert service.submit.call_count == 5
    user_id[0] = 2
    assert client.post('/api/debug', json=payload).status_code == 202
    user_id[0] = 1
    now[0] = 180
    assert client.post('/api/debug', json=payload).status_code == 202
    assert counter.counts['skyoj:ratelimit:submit:1:2'] == 12
    assert counter.counts['skyoj:ratelimit:submit:2:2'] == 1
    assert counter.counts['skyoj:ratelimit:submit:1:3'] == 1

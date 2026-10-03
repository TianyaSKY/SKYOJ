"""代码提交与调试的 JSON/表单校验错误保持结构化，非法 JSON 返回 422。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_debug_service, get_submission_service
from app.services.auth import AuthUserInfo


@pytest.fixture
def code_client(client, monkeypatch):
    from app.api import submission

    monkeypatch.setattr(submission, 'enforce', lambda *a, **kw: None)
    client.app.dependency_overrides[get_current_auth] = lambda: AuthContext(
        user=AuthUserInfo(id=7, username='student', role='student'),
    )
    service = MagicMock()
    service.submit.return_value = SimpleNamespace(submission_id=17, status='Pending', exam_id=None)
    service.create.return_value = SimpleNamespace(debug_run_id=18, status='Pending', exam_id=None)
    client.app.dependency_overrides[get_submission_service] = lambda: service
    client.app.dependency_overrides[get_debug_service] = lambda: service
    return client, service


@pytest.mark.parametrize('endpoint', ['/api/submissions/submit', '/api/debug'])
@pytest.mark.parametrize('payload', [b'{broken', b'', b'\xff\xff'])
def test_invalid_json_returns_validation_response(code_client, endpoint, payload):
    client, service = code_client
    response = client.post(endpoint, content=payload, headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.json()['code'] == 'HTTP_422'
    assert response.json()['detail'][0]['type'] == 'json_invalid'
    service.submit.assert_not_called()
    service.create.assert_not_called()


@pytest.mark.parametrize('endpoint', ['/api/submissions/submit', '/api/debug'])
@pytest.mark.parametrize('form', [False, True])
def test_code_field_errors_have_structured_body_locations(code_client, endpoint, form):
    client, service = code_client
    payload = {'problem_id': -1, 'code': 'print(1)', 'language': 'python'}
    response = client.post(endpoint, **({'data': payload} if form else {'json': payload}))
    assert response.status_code == 422
    assert response.json()['code'] == 'HTTP_422'
    detail = response.json()['detail']
    assert isinstance(detail, list)
    assert detail[0]['loc'] == ['body', 'problem_id']
    assert detail[0]['type'] == 'greater_than_equal'
    service.submit.assert_not_called()
    service.create.assert_not_called()


@pytest.mark.parametrize('endpoint', ['/api/submissions/submit', '/api/debug'])
def test_json_suffix_content_type_is_parsed(code_client, endpoint):
    client, _ = code_client
    response = client.post(endpoint, content='{"problem_id":1,"code":"print(1)","language":"python"}',
                           headers={'Content-Type': 'application/vnd.skyoj+json; charset=utf-8'})
    assert response.status_code == 202

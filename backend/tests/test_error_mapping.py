"""错误映射单轨化测试：业务异常统一由全局 handler 映射，信封键为 error。"""

from app.api.deps import get_llm_facade_service
from app.domain.errors import ExternalServiceError, LlmConfigError
from app.utils.auth_tools import AuthContext, get_current_auth


class _FakeUser:
    id = 1
    role = "teacher"


class _FakeLlmFacade:
    def __init__(self, exc):
        self._exc = exc

    def ask(self, params):
        raise self._exc


def _auth_teacher():
    return AuthContext(user=_FakeUser(), exam_id=-1)


def test_external_service_error_maps_to_502(client):
    client.app.dependency_overrides[get_current_auth] = _auth_teacher
    client.app.dependency_overrides[get_llm_facade_service] = lambda: _FakeLlmFacade(
        ExternalServiceError("上游 LLM 服务不可用")
    )

    response = client.post(
        "/api/llm/ask",
        json={"system_setting": "s", "prompt": "p"},
    )

    assert response.status_code == 502
    assert response.json() == {"error": "上游 LLM 服务不可用"}


def test_llm_config_error_maps_to_400(client):
    client.app.dependency_overrides[get_current_auth] = _auth_teacher
    client.app.dependency_overrides[get_llm_facade_service] = lambda: _FakeLlmFacade(
        LlmConfigError("LLM 环境变量未完整配置")
    )

    response = client.post(
        "/api/llm/ask",
        json={"system_setting": "s", "prompt": "p"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "LLM 环境变量未完整配置"}


def test_dataset_download_auth_error_uses_error_key(client):
    response = client.get("/api/datasets/1/download")

    assert response.status_code == 401
    assert "error" in response.json()
    assert "message" not in response.json()

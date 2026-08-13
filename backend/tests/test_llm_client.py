"""LLM 客户端（Responses API）单元测试。"""

import pytest

from app.clients.llm_client import LlmClient


class FakeResponsesResource:
    def __init__(self) -> None:
        self.last_kwargs: dict | None = None
        self.response = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


class FakeOpenAI:
    """替换 openai.OpenAI：记录构造参数，返回预置的 responses 结果。"""

    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.responses = FakeResponsesResource()


def _stub_response(output_text: str):
    class _Resp:
        def __init__(self) -> None:
            self.output = [object()]  # 非空即视为有效响应
            self.output_text = output_text

    return _Resp()


def _configured_client(monkeypatch, fake: FakeOpenAI) -> LlmClient:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_URL", "https://llm.example.com/v1")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setattr("openai.OpenAI", lambda api_key, base_url: fake)
    return LlmClient()


def test_chat_json_parses_responses_output(monkeypatch):
    fake = FakeOpenAI("k", "u")
    fake.responses.response = _stub_response('{"title": "两数之和"}')
    client = _configured_client(monkeypatch, fake)

    result = client.chat_json(
        system_setting="你是出题助手",
        prompt="请生成一道题",
        output_format={"title": "str"},
    )

    assert result == {"title": "两数之和"}
    kwargs = fake.responses.last_kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["stream"] is False
    assert kwargs["instructions"].startswith("你是出题助手")
    assert "请务必仅以 JSON 格式返回结果" in kwargs["instructions"]
    assert kwargs["input"] == [{"role": "user", "content": "请生成一道题"}]
    assert kwargs["text"] == {"format": {"type": "json_object"}}


def test_chat_json_without_output_format_omits_text(monkeypatch):
    fake = FakeOpenAI("k", "u")
    fake.responses.response = _stub_response('{"answer": 42}')
    client = _configured_client(monkeypatch, fake)

    client.chat_json(system_setting="s", prompt="p")

    assert "text" not in fake.responses.last_kwargs


def test_chat_json_non_openai_response_raises_with_hint(monkeypatch):
    fake = FakeOpenAI("k", "u")
    fake.responses.response = "<!doctype html>"
    client = _configured_client(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="LLM_API_URL"):
        client.chat_json(system_setting="s", prompt="p")


def test_chat_json_missing_format_key_raises(monkeypatch):
    fake = FakeOpenAI("k", "u")
    fake.responses.response = _stub_response('{"title": "x"}')
    client = _configured_client(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="缺失键"):
        client.chat_json(
            system_setting="s",
            prompt="p",
            output_format={"title": "str", "difficulty": "str"},
        )


def test_chat_json_invalid_json_content_raises(monkeypatch):
    fake = FakeOpenAI("k", "u")
    fake.responses.response = _stub_response("不是 JSON")
    client = _configured_client(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="LLM 请求失败"):
        client.chat_json(system_setting="s", prompt="p")


def test_chat_json_unconfigured_env_raises(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL_NAME", raising=False)

    with pytest.raises(RuntimeError, match="LLM environment variables"):
        LlmClient().chat_json(system_setting="s", prompt="p")

"""审计摘要不得保存请求凭据；正常操作上下文继续保留。"""

import json

import app.persistence  # noqa: F401
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.middleware.audit import AuditMiddleware, _summarize_payload
from app.persistence.database import Base
from app.persistence.system import AuditLog


def test_json_audit_redacts_password_and_preserves_business_fields():
    body = {"username": "alice", "password": "synthetic-password", "title": "考试"}
    summary = _summarize_payload(json.dumps(body).encode(), "application/json")
    parsed = json.loads(summary)
    assert parsed["username"] == "alice"
    assert parsed["title"] == "考试"
    assert parsed["password"] == "<redacted>"
    assert "synthetic-password" not in summary


def test_nested_credentials_are_redacted_before_truncation():
    body = {
        "settings": [{"LLM_API_KEY": "synthetic-key", "refresh_token": "synthetic-token"}],
        "nested": {"Authorization": "synthetic-auth", "Cookie": "synthetic-cookie"},
        "description": "x" * 2000,
    }
    summary = _summarize_payload(json.dumps(body).encode(), "application/json; charset=utf-8")
    for secret in ["synthetic-key", "synthetic-token", "synthetic-auth", "synthetic-cookie"]:
        assert secret not in summary
    assert "<redacted>" in summary
    assert len(summary) <= 1027


@pytest.mark.parametrize("payload,content_type,expected", [
    (b'{"password":"synthetic-password",', "application/json", "<invalid-json>"),
    (b'"synthetic-password"', "application/json", "<json>"),
    (b'synthetic-password', "text/plain", "<text>"),
    (b'\xff', "application/octet-stream", "<binary>"),
    (b'file-data', "multipart/form-data; boundary=test", "<multipart>"),
    (b'', "application/json", None),
])
def test_unstructured_payloads_are_not_logged_raw(payload, content_type, expected):
    assert _summarize_payload(payload, content_type) == expected


def test_form_audit_redacts_credentials_and_preserves_repeated_fields():
    summary = _summarize_payload(
        b'username=alice&password=synthetic-password&tag=a&tag=b',
        "application/x-www-form-urlencoded",
    )
    assert "synthetic-password" not in summary
    assert "username=alice" in summary
    assert "tag=a&tag=b" in summary


@pytest.mark.parametrize("content_type", ["", "application/vnd.test+json"])
def test_json_without_standard_media_type_still_redacts_password(content_type):
    summary = _summarize_payload(b'{"old_password":"synthetic-password"}', content_type)
    assert json.loads(summary)["old_password"] == "<redacted>"


def test_deeply_nested_payload_does_not_break_audit_or_log_raw_data():
    payload = b'[' * 1500 + b'{"password":"synthetic-password"}' + b']' * 1500
    assert _summarize_payload(payload, "application/json") == "<invalid-json>"


def test_middleware_persists_redacted_summary_and_operation_context(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.middleware.audit.SessionLocal", lambda: Session(engine))
    application = FastAPI()
    application.add_middleware(AuditMiddleware)

    @application.post("/api/auth/login")
    async def login(request: Request):
        body = await request.json()
        return {"ok": body["password"] == "synthetic-password"}

    try:
        with TestClient(application) as client:
            response = client.post(
                "/api/auth/login", json={"username": "alice", "password": "synthetic-password"}
            )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        with Session(engine) as db:
            entry = db.query(AuditLog).one()
            assert entry.method == "POST"
            assert entry.path == "/api/auth/login"
            assert entry.status_code == 200
            assert "synthetic-password" not in entry.payload_summary
            assert json.loads(entry.payload_summary)["username"] == "alice"
    finally:
        engine.dispose()

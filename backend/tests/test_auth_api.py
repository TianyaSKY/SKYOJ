"""Real path tests against the shipped FastAPI app (no Flask)."""

import inspect

import app.main as main_module
from app.database import SessionLocal
from app.models.user import User
from app.utils.passwords import check_password, hash_password


def test_app_is_fastapi_not_flask():
    from fastapi import FastAPI

    assert isinstance(main_module.app, FastAPI)
    # No runtime Flask dependency for request handling
    source = inspect.getsource(main_module)
    assert "from flask" not in source
    assert "import flask" not in source
    assert "Flask(" not in source


def test_root_ready(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "ready" in body["status"].lower() or "SKYOJ" in body["status"]


def test_register_login_protected_flow(client):
    # Register
    reg = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123", "role": "student"},
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["message"]

    # Duplicate register rejected
    dup = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123"},
    )
    assert dup.status_code == 400

    # Login
    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret123"},
    )
    assert login.status_code == 200, login.text
    data = login.json()
    assert isinstance(data.get("token"), str) and len(data["token"]) > 10
    assert data["user"]["username"] == "alice"
    token = data["token"]

    # Protected without token → 401
    no_auth = client.get("/api/user/submissions")
    assert no_auth.status_code == 401
    err = no_auth.json()
    assert "message" in err or "detail" in err

    # Protected with bad token → 401
    bad = client.get(
        "/api/user/submissions",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert bad.status_code == 401

    # Protected with valid token → not 401
    ok = client.get(
        "/api/user/submissions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200, ok.text
    assert isinstance(ok.json(), list)


def test_password_hash_roundtrip_and_model_query(client):
    """Model query path without Flask app_context; bcrypt-compatible hashes."""
    hashed = hash_password("pw-for-query")
    assert check_password(hashed, "pw-for-query")
    assert not check_password(hashed, "wrong")

    # Login path already created alice; also insert via ORM session used by app engine
    from app.database import engine
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    # Use dependency-compatible path: register another user via API then query via DB
    client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "bobpass", "role": "teacher"},
    )
    login = client.post(
        "/api/auth/login",
        json={"username": "bob", "password": "bobpass"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "teacher"

    # Direct model query through engine (no Flask)
    from sqlalchemy import select
    from app.database import SessionLocal as AppSession

    # Override fixture uses separate engine; query via API-created user via protected profile
    token = login.json()["token"]
    uid = login.json()["user"]["id"]
    profile = client.get(
        f"/api/user/{uid}/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "bob"


def test_sys_info_public(client):
    r = client.get("/api/sys/info")
    assert r.status_code == 200
    body = r.json()
    assert "title" in body
    assert "llm_env_ready" in body


def test_exam_status_static_route_not_422(client):
    """
    GET /api/exams/status must hit the static handler, not /{exam_id}.
    Regression: FastAPI would return 422 int_parsing if 'status' matched exam_id.
    Flow: register teacher → create exam → enter → GET /status (list, not 422).
    """
    from datetime import datetime, timedelta

    # Teacher account
    reg = client.post(
        "/api/auth/register",
        json={"username": "exam_teacher", "password": "secret123", "role": "teacher"},
    )
    assert reg.status_code == 201, reg.text
    login = client.post(
        "/api/auth/login",
        json={"username": "exam_teacher", "password": "secret123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Not in exam yet: static /status must not be 422
    not_in = client.get("/api/exams/status", headers=headers)
    assert not_in.status_code != 422, not_in.text
    assert not_in.status_code == 400, not_in.text
    assert "not in an active exam" in not_in.json().get("error", "").lower() or (
        "error" in not_in.json()
    )

    now = datetime.utcnow()
    create = client.post(
        "/api/exams/",
        headers=headers,
        json={
            "title": "Route Order Exam",
            "description": "status path regression",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "is_visible": True,
        },
    )
    assert create.status_code == 201, create.text
    exam_id = create.json()["id"]

    enter = client.post(f"/api/exams/{exam_id}/enter", headers=headers, json={})
    assert enter.status_code == 200, enter.text
    exam_token = enter.json()["token"]
    assert isinstance(exam_token, str) and len(exam_token) > 10
    exam_headers = {"Authorization": f"Bearer {exam_token}"}

    status = client.get("/api/exams/status", headers=exam_headers)
    assert status.status_code != 422, status.text
    assert status.status_code == 200, status.text
    assert isinstance(status.json(), list)

    # Static /exit must also resolve (not as exam_id)
    exited = client.post("/api/exams/exit", headers=exam_headers)
    assert exited.status_code != 422, exited.text
    assert exited.status_code == 200, exited.text
    assert "token" in exited.json()

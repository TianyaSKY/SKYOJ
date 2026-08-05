"""认证 API 安全回归测试。"""

from datetime import datetime, timedelta, timezone

import jwt


TEST_SECRET = "test-secret-key-for-milestone-one"


def test_public_registration_creates_student(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123"},
    )

    assert response.status_code == 201

    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret123"},
    )

    assert login.status_code == 200
    assert login.json()["user"]["role"] == "student"


def test_public_registration_rejects_role_field(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "hacker",
            "password": "secret123",
            "role": "teacher",
        },
    )

    assert response.status_code == 422


def test_login_succeeds_for_registered_student(client):
    client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "secret123"},
    )

    response = client.post(
        "/api/auth/login",
        json={"username": "bob", "password": "secret123"},
    )

    assert response.status_code == 200
    assert response.json()["token"]


def test_missing_token_returns_401(client):
    response = client.get("/api/user/submissions")

    assert response.status_code == 401
    assert response.json()["message"] == "Token 丢失"


def test_problems_list_requires_token(client):
    response = client.get("/api/problems")

    assert response.status_code == 401
    assert response.json()["message"] == "Token 丢失"


def test_invalid_token_returns_401(client):
    response = client.get(
        "/api/user/submissions",
        headers={"Authorization": "Bearer this-is-not-a-valid-token"},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid token"


def test_expired_token_returns_401(client):
    token = jwt.encode(
        {
            "sub": "1",
            "role": "student",
            "exam_id": -1,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/user/submissions",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Token has expired."

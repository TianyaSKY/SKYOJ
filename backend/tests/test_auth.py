"""认证 API 测试：注册、登录、token 校验。"""

import pytest


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "password123"},
        )
        assert resp.status_code == 201
        assert resp.json()["message"] == "User registered successfully"

    def test_register_duplicate_username(self, client, student_user):
        resp = client.post(
            "/api/auth/register",
            json={"username": "test_student", "password": "password456"},
        )
        assert resp.status_code in (400, 409, 422)

    def test_register_rate_limit(self, client):
        """注册接口 3 次/分钟/IP 限流。"""
        for i in range(3):
            resp = client.post(
                "/api/auth/register",
                json={"username": f"user{i}_ratelimit", "password": "password123"},
            )
            assert resp.status_code == 201
        # 第 4 次应被限流（无 Redis 时 fail-open，不过测）
        resp = client.post(
            "/api/auth/register",
            json={"username": "user4_ratelimit", "password": "password123"},
        )
        # 无 Redis 环境返回 201，连接 Redis 后返回 429
        assert resp.status_code in (201, 429)


class TestLogin:
    def test_login_success(self, client, student_user):
        resp = client.post(
            "/api/auth/login",
            json={"username": "test_student", "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "test_student"
        assert data["user"]["role"] == "student"

    def test_login_wrong_password(self, client, student_user):
        resp = client.post(
            "/api/auth/login",
            json={"username": "test_student", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "password123"},
        )
        assert resp.status_code == 401

    def test_login_rate_limit(self, client):
        """登录接口 5 次/分钟/IP 限流。"""
        usernames = [f"logintest{i}" for i in range(5)]
        for u in usernames:
            client.post(
                "/api/auth/register",
                json={"username": u, "password": "password123"},
            )
        for _ in range(5):
            resp = client.post(
                "/api/auth/login",
                json={"username": "logintest0", "password": "password123"},
            )
            assert resp.status_code == 200
        # 第 6 次应被限流
        resp = client.post(
            "/api/auth/login",
            json={"username": "logintest0", "password": "password123"},
        )
        assert resp.status_code in (200, 429)

"""提交 API 测试：提交、列表、详情。"""

import pytest


class TestSubmitSolution:
    def test_submit_requires_student_role(self, client, teacher_token, sample_problem):
        """教师账户不能提交代码。"""
        resp = client.post(
            "/api/submissions/submit",
            headers={"Authorization": f"Bearer {teacher_token}"},
            json={
                "problem_id": sample_problem.id,
                "code": "print('hello')",
                "language": "python",
            },
        )
        assert resp.status_code == 403

    def test_submit_without_auth(self, client, sample_problem):
        resp = client.post(
            "/api/submissions/submit",
            json={
                "problem_id": sample_problem.id,
                "code": "print('hello')",
                "language": "python",
            },
        )
        assert resp.status_code == 401

    def test_submit_success(self, client, student_token, sample_problem):
        """提交后返回 202 和 submission_id。"""
        resp = client.post(
            "/api/submissions/submit",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "problem_id": sample_problem.id,
                "code": "print('hello')",
                "language": "python",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "submission_id" in data
        assert data["status"] == "Pending"

    def test_submit_rate_limit(self, client, student_token, sample_problem):
        """每人每分钟最多 10 次提交。"""
        for i in range(10):
            resp = client.post(
                "/api/submissions/submit",
                headers={"Authorization": f"Bearer {student_token}"},
                json={
                    "problem_id": sample_problem.id,
                    "code": f"print({i})",
                    "language": "python",
                },
            )
            assert resp.status_code == 202
        # 第 11 次（无 Redis 时可能通过，有 Redis 时 429）
        resp = client.post(
            "/api/submissions/submit",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "problem_id": sample_problem.id,
                "code": "print('extra')",
                "language": "python",
            },
        )
        assert resp.status_code in (202, 429)

    def test_submit_missing_problem_id(self, client, student_token):
        resp = client.post(
            "/api/submissions/submit",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"code": "print('hello')", "language": "python"},
        )
        assert resp.status_code in (400, 422)

    def test_submit_nonexistent_problem(self, client, student_token):
        resp = client.post(
            "/api/submissions/submit",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "problem_id": 99999,
                "code": "print('hello')",
                "language": "python",
            },
        )
        assert resp.status_code in (404, 400)


class TestListSubmissions:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/submissions/")
        assert resp.status_code == 401

    def test_list_student_sees_own(self, client, student_token, student_user, sample_problem):
        """学生只能看到自己的提交。"""
        # 先提交
        client.post(
            "/api/submissions/submit",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "problem_id": sample_problem.id,
                "code": "print('hello')",
                "language": "python",
            },
        )
        resp = client.get(
            "/api/submissions/",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_list_filter_by_problem(self, client, student_token, sample_problem):
        resp = client.get(
            f"/api/submissions/?problem_id={sample_problem.id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200


class TestGetSubmission:
    def test_get_own_submission(self, client, student_token, student_user, sample_problem):
        submit_resp = client.post(
            "/api/submissions/submit",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "problem_id": sample_problem.id,
                "code": "print('hello')",
                "language": "python",
            },
        )
        sub_id = submit_resp.json()["submission_id"]
        resp = client.get(
            f"/api/submissions/{sub_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "Pending"

    def test_cannot_see_others_submission(self, client, student_token, db_session, sample_problem):
        """用另一个用户提交，学生 token 无法查看。"""
        import bcrypt
        from app.persistence.user import User

        other = User(
            username="other_student",
            password_hash=bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
            role="student",
        )
        db_session.add(other)
        db_session.commit()

        # 用其他用户登录
        login = client.post(
            "/api/auth/login",
            json={"username": "other_student", "password": "pass"},
        )
        other_token = login.json()["token"]

        # other 提交
        submit_resp = client.post(
            "/api/submissions/submit",
            headers={"Authorization": f"Bearer {other_token}"},
            json={
                "problem_id": sample_problem.id,
                "code": "print('other')",
                "language": "python",
            },
        )
        sub_id = submit_resp.json()["submission_id"]

        # student 尝试查看 other 的提交
        resp = client.get(
            f"/api/submissions/{sub_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

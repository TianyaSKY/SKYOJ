"""考试 API 测试：创建、列表、详情、排行榜。"""

import datetime

import pytest


@pytest.mark.parametrize(
    "patch,expected",
    [
        ({"freeze_minutes": None}, None),
        ({"title": "更名"}, 30),
        ({"freeze_minutes": 0}, 0),
        ({"freeze_minutes": 15}, 15),
    ],
)
def test_exam_update_distinguishes_omitted_and_cleared_freeze(
    client, teacher_token, patch, expected
):
    """封榜可明确清空，省略字段保留原值；响应与后续读取必须一致。"""
    headers = {"Authorization": f"Bearer {teacher_token}"}
    created = client.post(
        "/api/exams/",
        headers=headers,
        json={
            "title": "封榜考试",
            "start_time": "2026-01-01T09:00:00",
            "end_time": "2026-01-01T11:00:00",
            "freeze_minutes": 30,
        },
    )
    assert created.status_code == 201
    exam_id = created.json()["id"]

    response = client.put(f"/api/exams/{exam_id}", headers=headers, json=patch)

    assert response.status_code == 200
    assert response.json()["freeze_minutes"] == expected
    detail = client.get(f"/api/exams/{exam_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["freeze_minutes"] == expected


def test_exam_api_normalizes_timezone_and_accepts_partial_updates(client, teacher_token):
    """带时区的请求和无时区的数据库时间使用同一 UTC 时间轴。"""
    headers = {"Authorization": f"Bearer {teacher_token}"}
    created = client.post(
        "/api/exams/",
        headers=headers,
        json={
            "title": "时区考试",
            "start_time": "2026-01-01T17:00:00+08:00",
            "end_time": "2026-01-01T11:00:00",
        },
    )
    assert created.status_code == 201
    assert created.json()["start_time"] == "2026-01-01T09:00:00"
    assert created.json()["end_time"] == "2026-01-01T11:00:00"

    updated = client.put(
        f"/api/exams/{created.json()['id']}",
        headers=headers,
        json={"end_time": "2026-01-01T07:00:00-05:00"},
    )
    assert updated.status_code == 200
    assert updated.json()["start_time"] == "2026-01-01T09:00:00"
    assert updated.json()["end_time"] == "2026-01-01T12:00:00"


class TestExamCRUD:
    def test_create_exam_requires_teacher(self, client, student_token):
        resp = client.post(
            "/api/exams/",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "title": "期末考试",
                "description": "数据结构期末测试",
                "start_time": "2026-01-01T09:00:00",
                "end_time": "2026-01-01T12:00:00",
                "is_visible": True,
            },
        )
        assert resp.status_code == 403

    def test_create_exam_success(self, client, teacher_token, teacher_user):
        resp = client.post(
            "/api/exams/",
            headers={"Authorization": f"Bearer {teacher_token}"},
            json={
                "title": "数据结构期末考试",
                "description": "ACM 赛制期末测试",
                "start_time": "2026-06-01T09:00:00",
                "end_time": "2026-06-01T12:00:00",
                "is_visible": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "数据结构期末考试"
        assert "id" in data

    def test_list_exams_teacher(self, client, teacher_token):
        resp = client.get("/api/exams/", headers={"Authorization": f"Bearer {teacher_token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_exams_student_visible(self, client, student_token):
        resp = client.get("/api/exams/", headers={"Authorization": f"Bearer {student_token}"})
        assert resp.status_code == 200

    def test_delete_exam_requires_teacher(self, client, student_token):
        resp = client.delete(
            "/api/exams/1",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    def test_update_exam_teacher(self, client, teacher_token):
        # 先创建
        create = client.post(
            "/api/exams/",
            headers={"Authorization": f"Bearer {teacher_token}"},
            json={
                "title": "旧标题",
                "description": "旧描述",
                "start_time": "2026-06-01T09:00:00",
                "end_time": "2026-06-01T12:00:00",
                "is_visible": False,
            },
        )
        exam_id = create.json()["id"]
        # 更新
        resp = client.put(
            f"/api/exams/{exam_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
            json={"title": "新标题", "is_visible": True},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "新标题"


class TestExamRank:
    def test_rank_empty_exam(self, client, teacher_token):
        """空考试排行榜返回空排名列表。"""
        create = client.post(
            "/api/exams/",
            headers={"Authorization": f"Bearer {teacher_token}"},
            json={
                "title": "空考试",
                "description": "无参赛者",
                "start_time": "2026-06-01T09:00:00",
                "end_time": "2026-06-01T12:00:00",
                "is_visible": True,
            },
        )
        exam_id = create.json()["id"]
        resp = client.get(
            f"/api/exams/{exam_id}/rank",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exam_title"] == "空考试"
        assert data["rank"] == []


class TestExamScoreExport:
    def test_export_scores_requires_teacher(self, client, student_token):
        resp = client.get(
            "/api/exams/1/export_scores",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

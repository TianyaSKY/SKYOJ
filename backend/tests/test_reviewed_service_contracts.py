"""动态 JSON、身份校验和查重响应的实际契约。"""

from unittest.mock import MagicMock

import pytest
from app.core.errors import PermissionDeniedError
from app.services.llm import AskLlmParams
from app.persistence.submission import PlagiarismReport
from app.persistence.submission import SubmissionRepository
from app.services.llm import LlmFacadeService


def test_llm_context_uses_injected_repository_and_preserves_dynamic_result():
    client = MagicMock()
    client.is_configured.return_value = True
    client.chat_json.return_value = {"nested": {"count": 1}, "ok": True}
    repo = MagicMock()
    repo.get_by_id.return_value = MagicMock(
        id=3, user_id=1, language="python", status="Accepted", code_content="print(1)"
    )
    service = LlmFacadeService(client, repo)
    result = service.ask(
        AskLlmParams("system", "question", "teacher", context_submission_id=3)
    )
    assert result.payload == {"nested": {"count": 1}, "ok": True}
    repo.get_by_id.assert_called_once_with(3)
    assert "print(1)" in client.chat_json.call_args.kwargs["system_setting"]
    with pytest.raises(PermissionDeniedError):
        service.ask(AskLlmParams("system", "question", "student"))
    with pytest.raises(PermissionDeniedError):
        service.ask_stream(AskLlmParams("system", "question", "student"))
    client.chat_json.assert_called_once()


def test_system_config_and_statistics_http_contract(
    client, teacher_token, student_token
):
    headers = {"Authorization": f"Bearer {teacher_token}"}
    response = client.put(
        "/api/sys/info",
        json={"title": "课堂", "practice": False, "custom_key": [1, 2]},
        headers=headers,
    )
    assert response.status_code == 200
    assert set(response.json()["updated_keys"]) == {"title", "practice", "custom_key"}
    info = client.get("/api/sys/info").json()
    assert info["title"] == "课堂"
    assert info["practice"] is False
    stats = client.get("/api/sys/statistics", headers=headers)
    assert stats.status_code == 200
    assert set(stats.json()) == {
        "today_submissions",
        "total_problems",
        "total_users",
        "exams_in_period",
    }
    assert (
        client.put(
            "/api/sys/info",
            json={"title": "越权"},
            headers={"Authorization": f"Bearer {student_token}"},
        ).status_code
        == 403
    )


def test_plagiarism_dataclass_serialization_and_access_control(
    client, db_session, teacher_token, student_token, student_user, sample_problem
):
    repo = SubmissionRepository(db_session)
    a = repo.create(student_user.id, sample_problem.id, None, "python", "x=1")
    b = repo.create(student_user.id, sample_problem.id, None, "python", "x=2")
    db_session.add(
        PlagiarismReport(
            problem_id=sample_problem.id,
            submission_a_id=a.id,
            submission_b_id=b.id,
            similarity_score=0.8,
            status="completed",
            matched_blocks=[
                {
                    "start_a": 1,
                    "end_a": 1,
                    "start_b": 1,
                    "end_b": 1,
                    "code_a": "x=1",
                    "code_b": "x=2",
                }
            ],
        )
    )
    db_session.commit()
    teacher = {"Authorization": f"Bearer {teacher_token}"}
    student = {"Authorization": f"Bearer {student_token}"}
    response = client.get(
        f"/api/plagiarism/problem/{sample_problem.id}", headers=teacher
    )
    assert response.status_code == 200
    report = response.json()["reports"][0]
    assert report["username_a"] == student_user.username
    assert report["matched_blocks"][0]["code_a"] == "x=1"
    assert (
        client.get(
            f"/api/plagiarism/problem/{sample_problem.id}", headers=student
        ).status_code
        == 403
    )
    assert (
        client.get(f"/api/plagiarism/reports/{a.id}", headers=student).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/plagiarism/problem/{sample_problem.id}?page=0", headers=teacher
        ).status_code
        == 422
    )

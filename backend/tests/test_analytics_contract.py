"""聚合查询与权限、响应契约的回归测试。"""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from app.domain.errors import PermissionDeniedError
from app.models.submission import Submission
from app.repositories.submission_repository import SubmissionRepository
from app.services.submission_service import SubmissionService
from app.utils.time import utcnow


def test_analytics_aggregates_counts_without_loading_source_rows(
    db_session, student_user, sample_problem
):
    now = utcnow()
    db_session.add_all(
        [
            Submission(
                user_id=student_user.id,
                problem_id=sample_problem.id,
                status="Accepted",
                created_at=now,
                language="python",
            ),
            Submission(
                user_id=student_user.id,
                problem_id=sample_problem.id,
                status="Wrong Answer",
                created_at=now - timedelta(days=40),
                language="python",
            ),
        ]
    )
    db_session.flush()
    service = SubmissionService(SubmissionRepository(db_session), MagicMock())
    result = service.get_platform_analytics("teacher")
    assert (result.total_submissions, result.total_accepted, result.total_problems) == (
        2,
        1,
        1,
    )
    assert result.global_pass_rate == 0.5
    assert result.problem_pass_rates[0].pass_rate == 0.5
    assert [(row.date, row.count) for row in result.daily_submissions] == [
        (now.date().isoformat(), 1)
    ]
    assert result.problem_difficulty[0].difficulty > 0
    with pytest.raises(PermissionDeniedError):
        service.get_platform_analytics("student")


def test_analytics_empty_database(db_session):
    result = SubmissionService(
        SubmissionRepository(db_session), MagicMock()
    ).get_platform_analytics("teacher")
    assert result.total_submissions == 0
    assert result.global_pass_rate == 0
    assert (
        result.problem_pass_rates
        == result.problem_difficulty
        == result.daily_submissions
        == []
    )


def test_analytics_http_contract(client, teacher_token, student_token):
    response = client.get(
        "/api/admin/analytics", headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert response.status_code == 200
    assert response.json()["total_submissions"] == 0
    assert (
        client.get(
            "/api/admin/analytics", headers={"Authorization": f"Bearer {student_token}"}
        ).status_code
        == 403
    )

"""调试运行遵守考试会话、开放时间和题目范围，拒绝时不投递任务。"""

from types import SimpleNamespace
from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_debug_service
from app.core.errors import InvalidStateError, PermissionDeniedError
from app.core.time import utcnow
from app.persistence.exam import Exam, ExamProblem
from app.persistence.submission import DebugRunRepository
from app.services.auth import AuthUserInfo
from app.services.debug import CreateDebugRunParams, DebugService


@pytest.fixture
def debug_service():
    repo, jobs = MagicMock(), MagicMock()
    repo.get_problem.return_value = SimpleNamespace(type='acm', language='python')
    repo.get_active_exam.return_value = SimpleNamespace(id=8)
    repo.get_exam_problem.return_value = SimpleNamespace(problem_id=1)
    repo.create.return_value = SimpleNamespace(id=9)
    return DebugService(repo, jobs, uow=MagicMock()), repo, jobs


@pytest.mark.parametrize('exam_id,session_exam_id', [(8, -1), (7, 8)])
def test_debug_cannot_choose_exam_without_matching_session(debug_service, exam_id, session_exam_id):
    service, repo, jobs = debug_service
    with pytest.raises(PermissionDeniedError):
        service.create(CreateDebugRunParams(1, 1, 'python', 'x', exam_id, session_exam_id), requester_role='student')
    repo.create.assert_not_called()
    jobs.enqueue_debug_submission.assert_not_called()


@pytest.mark.parametrize('expired', [True, False])
def test_debug_rejects_expired_exam_or_unrelated_problem(debug_service, expired):
    service, repo, jobs = debug_service
    if expired:
        repo.get_active_exam.return_value = None
    else:
        repo.get_exam_problem.return_value = None
    with pytest.raises(InvalidStateError if expired else PermissionDeniedError):
        service.create(CreateDebugRunParams(1, 1, 'python', 'x', 8, 8), requester_role='student')
    repo.create.assert_not_called()
    jobs.enqueue_debug_submission.assert_not_called()


@pytest.mark.parametrize('exam_id', [None, -1, 8])
def test_debug_uses_current_exam_when_body_omits_it(debug_service, exam_id):
    service, repo, jobs = debug_service
    result = service.create(CreateDebugRunParams(1, 1, 'python', 'x', exam_id, 8), requester_role='student')
    assert result.exam_id == 8
    assert repo.create.call_args.kwargs['exam_id'] == 8
    repo.get_exam_problem.assert_called_once_with(8, 1)
    jobs.enqueue_debug_submission.assert_called_once_with(9)


def test_practice_debug_does_not_query_exam(debug_service):
    service, repo, _ = debug_service
    result = service.create(CreateDebugRunParams(1, 1, 'python', 'x'), requester_role='student')
    assert result.exam_id is None
    repo.get_active_exam.assert_not_called()
    repo.get_exam_problem.assert_not_called()


def test_api_passes_authenticated_exam_session(client, debug_service):
    service, repo, _ = debug_service
    client.app.dependency_overrides[get_current_auth] = lambda: AuthContext(
        user=AuthUserInfo(id=1, username='student', role='student'), exam_id=8,
    )
    client.app.dependency_overrides[get_debug_service] = lambda: service
    response = client.post('/api/debug', json={'problem_id': 1, 'language': 'python', 'code': 'x'})
    assert response.status_code == 202
    assert response.json()['exam_id'] == 8
    assert repo.create.call_args.kwargs['exam_id'] == 8


def test_debug_repository_uses_real_exam_membership(db_session, sample_problem, teacher_user):
    now = utcnow()
    exam = Exam(title='考试', start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1), created_by=teacher_user.id)
    db_session.add(exam)
    db_session.flush()
    db_session.add(ExamProblem(exam_id=exam.id, problem_id=sample_problem.id, display_id='A'))
    db_session.flush()
    repo = DebugRunRepository(db_session)
    assert repo.get_exam_problem(exam.id, sample_problem.id) is not None
    assert repo.get_exam_problem(exam.id, 99999) is None

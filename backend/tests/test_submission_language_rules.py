"""服务端落实题目语言限制，拒绝请求时不能保存附件或创建异步任务。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_debug_service, get_submission_service
from app.core.errors import InvalidStateError
from app.services.auth import AuthUserInfo
from app.services.debug import DebugService
from app.services.submission import SubmissionService, SubmitParams


@pytest.fixture
def services():
    repo = MagicMock()
    repo.get_problem.return_value = SimpleNamespace(type='acm', language='python')
    repo.create.return_value = SimpleNamespace(id=17)
    jobs, storage, uow = MagicMock(), MagicMock(), MagicMock()
    submit = SubmissionService(repo, jobs, storage, uow=uow)
    debug = DebugService(repo, jobs, uow=uow)
    return repo, jobs, storage, submit, debug


@pytest.mark.parametrize('endpoint', ['/api/submissions/submit', '/api/debug'])
@pytest.mark.parametrize('language', ['cpp', 'csv', 'rust'])
def test_api_rejects_language_before_creating_submission(client, monkeypatch, services, endpoint, language):
    from app.api import submission

    monkeypatch.setattr(submission, 'enforce', lambda *a, **kw: None)
    repo, jobs, storage, submit, debug = services
    client.app.dependency_overrides[get_current_auth] = lambda: AuthContext(
        user=AuthUserInfo(id=1, username='student', role='student'),
    )
    client.app.dependency_overrides[get_submission_service] = lambda: submit
    client.app.dependency_overrides[get_debug_service] = lambda: debug
    response = client.post(endpoint, json={'problem_id': 1, 'code': 'x', 'language': language})
    assert response.status_code == 400
    assert response.json()['code'] == 'INVALID_STATE'
    repo.create.assert_not_called()
    jobs.enqueue_judge_submission.assert_not_called()
    jobs.enqueue_debug_submission.assert_not_called()
    storage.save.assert_not_called()


@pytest.mark.parametrize('problem_type,language,file_upload', [
    ('acm', 'python', True), ('oop', 'python', True),
    ('oop', 'cpp', False), ('kaggle', 'python', False), ('unknown', 'python', False),
])
def test_incompatible_submission_does_not_write_or_enqueue(services, problem_type, language, file_upload):
    repo, jobs, storage, submit, _ = services
    repo.get_problem.return_value.type = problem_type
    with pytest.raises(InvalidStateError):
        submit.submit(SubmitParams(
            user_id=1, problem_id=1, code='x', language=language,
            is_file_upload=file_upload, filename='answer.csv', file_content=b'data',
        ), requester_role='student')
    repo.create.assert_not_called()
    storage.save.assert_not_called()
    jobs.enqueue_judge_submission.assert_not_called()


@pytest.mark.parametrize('problem_type,allowed,language', [
    ('acm', 'python', 'python'), ('acm', 'java', 'java'),
    ('oop', 'c', 'c'), ('oop', 'cpp', 'cpp'),
    ('acm', ' Python, CPP ', 'cpp'), ('acm', '', 'java'),
    ('kaggle', 'python', 'csv'),
])
def test_allowed_languages_and_inline_csv_are_preserved(services, problem_type, allowed, language):
    repo, jobs, storage, submit, _ = services
    repo.get_problem.return_value = SimpleNamespace(type=problem_type, language=allowed)
    result = submit.submit(SubmitParams(1, 1, 'content', language), requester_role='student')
    assert result.submission_id == 17
    assert repo.create.call_args.args[3] == language
    jobs.enqueue_judge_submission.assert_called_once_with(17)
    storage.save.assert_not_called()

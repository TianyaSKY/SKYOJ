"""实时判题订阅与 HTTP 提交详情使用一致的身份和归属校验。"""

from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.auth_tokens import encode_auth_token
from app.core.config import SECRET_KEY
from app.persistence.submission import SubmissionRepository


@pytest.fixture
def redis_subscription(monkeypatch):
    from app.api import submission

    pubsub = MagicMock()
    pubsub.get_message.return_value = {'type': 'message', 'data': '{"status":"Accepted"}'}
    redis = MagicMock()
    redis.pubsub.return_value = pubsub
    monkeypatch.setattr(submission.redis_client, 'get_client', lambda: redis)
    return redis, pubsub


def test_student_cannot_subscribe_to_another_users_submission(
    client, db_session, student_user, teacher_user, sample_problem, redis_subscription
):
    record = SubmissionRepository(db_session).create(teacher_user.id, sample_problem.id, None, 'python', 'code')
    token = encode_auth_token(student_user.id, 'student')
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f'/api/submissions/ws/{record.id}?token={token}'):
            pass
    assert error.value.code == 4003
    redis_subscription[0].pubsub.assert_not_called()


@pytest.mark.parametrize('teacher', [False, True])
def test_owner_and_teacher_can_receive_submission_result(
    client, db_session, student_user, teacher_user, sample_problem, redis_subscription, teacher
):
    record = SubmissionRepository(db_session).create(student_user.id, sample_problem.id, None, 'python', 'code')
    db_session.commit()
    user = teacher_user if teacher else student_user
    token = encode_auth_token(user.id, user.role)
    with client.websocket_connect(f'/api/submissions/ws/{record.id}?token={token}') as websocket:
        assert websocket.receive_json() == {'status': 'Accepted'}
    redis_subscription[1].subscribe.assert_called_once_with(f'skyoj:submission:{record.id}')
    redis_subscription[1].close.assert_called_once()


def test_missing_submission_is_rejected_before_redis(
    client, student_user, redis_subscription
):
    token = encode_auth_token(student_user.id, 'student')
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f'/api/submissions/ws/999999?token={token}'):
            pass
    assert error.value.code == 4004
    redis_subscription[0].pubsub.assert_not_called()


def test_already_completed_result_is_delivered_without_redis(
    client, db_session, student_user, sample_problem, redis_subscription
):
    repo = SubmissionRepository(db_session)
    record = repo.create(student_user.id, sample_problem.id, None, 'python', 'code')
    repo.update_result(record.id, status='Accepted', score=100, output_log='完成')
    db_session.commit()
    token = encode_auth_token(student_user.id, 'student')
    with client.websocket_connect(f'/api/submissions/ws/{record.id}?token={token}') as websocket:
        assert websocket.receive_json() == {
            'submission_id': record.id, 'status': 'Accepted', 'score': 100, 'output_log': '完成',
        }
    redis_subscription[0].pubsub.assert_not_called()


def test_result_completed_during_subscription_is_delivered_from_database(
    client, db_session, student_user, sample_problem, redis_subscription
):
    repo = SubmissionRepository(db_session)
    record = repo.create(student_user.id, sample_problem.id, None, 'python', 'code')
    db_session.commit()

    def complete(*args):
        repo.update_result(record.id, status='Wrong Answer', score=0, output_log='判题完成')
        db_session.commit()

    redis_subscription[1].subscribe.side_effect = complete
    token = encode_auth_token(student_user.id, 'student')
    with client.websocket_connect(f'/api/submissions/ws/{record.id}?token={token}') as websocket:
        assert websocket.receive_json()['status'] == 'Wrong Answer'
    redis_subscription[1].get_message.assert_not_called()
    redis_subscription[1].close.assert_called_once()


def test_token_for_nonexistent_user_is_rejected_before_redis(client, redis_subscription):
    token = encode_auth_token(999999, 'teacher')
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f'/api/submissions/ws/1?token={token}'):
            pass
    assert error.value.code == 4001
    redis_subscription[0].pubsub.assert_not_called()


def test_token_role_cannot_override_current_database_role(
    client, db_session, student_user, teacher_user, sample_problem, redis_subscription
):
    record = SubmissionRepository(db_session).create(teacher_user.id, sample_problem.id, None, 'python', 'code')
    token = encode_auth_token(student_user.id, 'teacher')
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f'/api/submissions/ws/{record.id}?token={token}'):
            pass
    assert error.value.code == 4003
    redis_subscription[0].pubsub.assert_not_called()


@pytest.mark.parametrize('kind', ['invalid', 'expired'])
def test_invalid_authentication_is_rejected_before_redis(
    client, student_user, redis_subscription, kind
):
    token = 'invalid-token' if kind == 'invalid' else jwt.encode({
        'sub': str(student_user.id), 'role': 'student',
        'exp': datetime.now(timezone.utc) - timedelta(minutes=1),
    }, SECRET_KEY, algorithm='HS256')
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f'/api/submissions/ws/1?token={token}'):
            pass
    assert error.value.code == 4001
    redis_subscription[0].pubsub.assert_not_called()

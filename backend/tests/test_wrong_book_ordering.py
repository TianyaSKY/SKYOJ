"""错题状态按提交先后更新，不随异步判题的完成顺序倒退。"""

from datetime import datetime, timedelta

import pytest

from app.persistence.submission import Submission
from app.persistence.unit_of_work import UnitOfWork
from app.persistence.user import WrongBookRepository
from app.services.wrong_book import WrongBookService


@pytest.mark.parametrize('same_time', [False, True])
@pytest.mark.parametrize('newer_status', ['Accepted', 'Wrong Answer'])
def test_older_judge_result_cannot_reverse_newer_result(
    db_session, student_user, sample_problem, same_time, newer_status
):
    older = Submission(user_id=student_user.id, problem_id=sample_problem.id,
                       created_at=datetime(2026, 1, 1), status='Pending')
    newer = Submission(user_id=student_user.id, problem_id=sample_problem.id,
                       created_at=older.created_at + timedelta(seconds=0 if same_time else 1),
                       status='Pending')
    db_session.add_all([older, newer])
    db_session.commit()
    service = WrongBookService(WrongBookRepository(db_session), uow=UnitOfWork(db_session))
    # 先建立错题记录，再让更新的提交先完成判题。
    service.on_judge_complete(student_user.id, sample_problem.id, older.id, 'Wrong Answer')
    newer.status = newer_status
    service.on_judge_complete(student_user.id, sample_problem.id, newer.id, newer_status)
    before, _ = service.list_for_user(student_user.id)
    before = before[0]
    older.status = 'Wrong Answer' if newer_status == 'Accepted' else 'Accepted'
    service.on_judge_complete(student_user.id, sample_problem.id, older.id, older.status)
    after, _ = service.list_for_user(student_user.id)
    assert after[0] == before
    assert after[0].accepted == (newer_status == 'Accepted')
    if newer_status == 'Wrong Answer':
        assert after[0].submission_id == newer.id


@pytest.mark.parametrize('newer_status', ['Pending', 'Judging', 'Compile Error'])
def test_newer_attempt_without_learning_result_does_not_block_wrong_book(
    db_session, student_user, sample_problem, newer_status
):
    older = Submission(user_id=student_user.id, problem_id=sample_problem.id,
                       created_at=datetime(2026, 1, 1), status='Wrong Answer')
    newer = Submission(user_id=student_user.id, problem_id=sample_problem.id,
                       created_at=datetime(2026, 1, 2), status=newer_status)
    db_session.add_all([older, newer])
    db_session.commit()
    service = WrongBookService(WrongBookRepository(db_session), uow=UnitOfWork(db_session))
    service.on_judge_complete(student_user.id, sample_problem.id, older.id, 'Wrong Answer')
    items, total = service.list_for_user(student_user.id)
    assert total == 1
    assert items[0].submission_id == older.id
    assert not items[0].accepted


@pytest.mark.parametrize('newer_status', ['Accepted', 'Wrong Answer'])
def test_worker_saves_both_results_without_reversing_wrong_book(
    db_session, student_user, sample_problem, monkeypatch, newer_status
):
    from app.services import judge

    older_status = 'Wrong Answer' if newer_status == 'Accepted' else 'Accepted'
    older = Submission(user_id=student_user.id, problem_id=sample_problem.id,
                       created_at=datetime(2026, 1, 1), status='Pending')
    newer = Submission(user_id=student_user.id, problem_id=sample_problem.id,
                       created_at=datetime(2026, 1, 2), status='Pending')
    db_session.add_all([older, newer])
    db_session.commit()
    results = {older.id: older_status, newer.id: newer_status}
    monkeypatch.setattr(judge, 'run_acm_judge', lambda sid, *a, **kw: (results[sid], 0, '', []))
    monkeypatch.setattr(judge, '_publish_realtime_result', lambda *a: None)
    monkeypatch.setattr(judge, '_enqueue_plagiarism_scan', lambda *a: None)
    judge.judge_submission(newer.id, db_session)
    judge.judge_submission(older.id, db_session)
    db_session.expire_all()
    assert db_session.get(Submission, older.id).status == older_status
    assert db_session.get(Submission, newer.id).status == newer_status
    service = WrongBookService(WrongBookRepository(db_session), uow=UnitOfWork(db_session))
    items, total = service.list_for_user(student_user.id, unresolved_only=True)
    if newer_status == 'Accepted':
        assert total == 0 and items == []
    else:
        assert total == 1 and items[0].submission_id == newer.id

"""同时间戳提交在分页列表和个人记录中使用 ID 确定先后。"""

from datetime import datetime
from sqlalchemy import text

from app.persistence.submission import Submission, SubmissionRepository
from app.persistence.user import UserRepository


def test_submission_pages_and_profile_put_newer_tied_ids_first(
    db_session, student_user, sample_problem
):
    rows = [
        Submission(
            user_id=student_user.id, problem_id=sample_problem.id,
            created_at=datetime(2026, 1, 1), status="Accepted", score=100,
        )
        for _ in range(3)
    ]
    db_session.add_all(rows)
    db_session.commit()
    expected_ids = sorted((row.id for row in rows), reverse=True)
    # 使用另一种可满足时间排序的索引，暴露缺少 ID 排序时的歧义。
    db_session.execute(text(
        "CREATE INDEX ix_test_user_time ON submissions (user_id, created_at DESC, id ASC)"
    ))
    repository = SubmissionRepository(db_session)

    actual_ids = []
    for page in range(1, 4):
        items, total, pages = repository.list_all(
            None, student_user.id, None, None, None, page, 1
        )
        assert total == 3
        assert pages == 3
        actual_ids.extend(item.id for item in items)
    assert actual_ids == expected_ids
    assert [item.id for item in UserRepository(db_session).list_submissions(student_user.id)] == expected_ids

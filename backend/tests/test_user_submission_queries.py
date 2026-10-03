"""个人提交历史批量读取关系，查询次数不随每道题目增长。"""

import pytest
from sqlalchemy import event

from app.persistence.problem import Problem
from app.persistence.submission import Submission
from app.persistence.user import User, UserRepository
from app.services.user import to_user_submission_item


@pytest.mark.parametrize('count', [0, 1, 8])
def test_profile_submission_history_batches_relationships(db_session, count):
    user = User(username='history_student', password_hash='test', role='student')
    db_session.add(user)
    db_session.flush()
    user_id = user.id
    for index in range(count):
        problem = Problem(title=f'历史题目{index}', content='内容', type='acm', language='python')
        db_session.add(problem)
        db_session.flush()
        db_session.add(Submission(
            user_id=user_id, problem_id=problem.id, status='Accepted', score=100,
            language='python', code_content=f'print({index})',
        ))
    db_session.commit()
    # 清空身份映射，避免测试中的已加载关系掩盖真实请求的逐条查询。
    db_session.expunge_all()
    statements = []
    connection = db_session.connection()

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement)

    event.listen(connection, 'before_cursor_execute', capture)
    try:
        records = UserRepository(db_session).list_submissions(user_id)
        assert len(statements) <= 3, f'个人提交历史触发了 {len(statements)} 次读取'
        db_session.expunge_all()
        items = [to_user_submission_item(record) for record in records]
        assert {item.problem_title for item in items} == {f'历史题目{i}' for i in range(count)}
        assert all(record.user.username == 'history_student' for record in records)
        assert all(item.status == 'Accepted' and item.score == 100 for item in items)
        assert len(items) == count
        assert len(statements) <= 3
    finally:
        event.remove(connection, 'before_cursor_execute', capture)

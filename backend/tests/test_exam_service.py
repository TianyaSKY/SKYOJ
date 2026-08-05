"""考试服务批量查询与 N+1 修复回归测试。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401
from app.models.exam import Exam, ExamProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.repositories.exam_repository import ExamRepository
from app.services.exam_service import ExamService

T0 = datetime(2026, 1, 1, 9, 0, 0)


@pytest.fixture()
def seeded():
    """构造一库：两个学生、两道题、一场考试，含重复提交。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    alice = User(username="alice", password_hash="x", role="student")
    bob = User(username="bob", password_hash="x", role="student")
    teacher = User(username="t", password_hash="x", role="teacher")
    session.add_all([alice, bob, teacher])
    session.flush()

    p1 = Problem(title="P1", content="c1", type="acm", language="python")
    p2 = Problem(title="P2", content="c2", type="acm", language="python")
    session.add_all([p1, p2])
    session.flush()

    exam = Exam(
        title="期中考试",
        description="d",
        start_time=T0,
        end_time=T0 + timedelta(hours=2),
        is_visible=True,
        created_by=teacher.id,
    )
    session.add(exam)
    session.flush()

    ep1 = ExamProblem(exam_id=exam.id, problem_id=p1.id, display_id="A", score=100)
    ep2 = ExamProblem(exam_id=exam.id, problem_id=p2.id, display_id="B", score=100)
    session.add_all([ep1, ep2])
    session.flush()

    def add_submission(user, problem, status, score, offset_seconds):
        submission = Submission(
            user_id=user.id,
            problem_id=problem.id,
            exam_id=exam.id,
            status=status,
            score=score,
            created_at=T0 + timedelta(seconds=offset_seconds),
        )
        session.add(submission)
        return submission

    # alice P1 先错后对：latest 应为 Accepted 那条
    wa = add_submission(alice, p1, "Wrong Answer", 0, 60)
    ac1 = add_submission(alice, p1, "Accepted", 100, 300)
    ac2 = add_submission(alice, p2, "Accepted", 100, 600)
    # bob P1 只提交一次 WA
    wa_bob = add_submission(bob, p1, "Wrong Answer", 0, 120)
    session.commit()

    service = ExamService(ExamRepository(session))
    yield {
        "session": session,
        "service": service,
        "repository": ExamRepository(session),
        "alice": alice,
        "bob": bob,
        "teacher": teacher,
        "p1": p1,
        "p2": p2,
        "exam": exam,
        "wa": wa,
        "ac1": ac1,
        "ac2": ac2,
        "wa_bob": wa_bob,
    }
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_list_latest_submissions_returns_latest_per_pair(seeded):
    latest = seeded["repository"].list_latest_submissions(seeded["exam"].id)

    assert latest[(seeded["alice"].id, seeded["p1"].id)] is seeded["ac1"]
    assert latest[(seeded["alice"].id, seeded["p2"].id)] is seeded["ac2"]
    assert latest[(seeded["bob"].id, seeded["p1"].id)] is seeded["wa_bob"]
    assert len(latest) == 3


def test_list_latest_submissions_respects_filters(seeded):
    latest = seeded["repository"].list_latest_submissions(
        seeded["exam"].id,
        user_ids=[seeded["bob"].id],
        problem_ids=[seeded["p1"].id],
    )

    assert latest == {(seeded["bob"].id, seeded["p1"].id): seeded["wa_bob"]}


def test_get_status_takes_latest_submission(seeded):
    statuses = seeded["service"].get_status(seeded["alice"].id, seeded["exam"].id)

    assert [item.problem_id for item in statuses] == [seeded["p1"].id, seeded["p2"].id]
    assert [item.title for item in statuses] == ["P1", "P2"]
    assert statuses[0].status == "Accepted"
    assert statuses[0].current_score == 100
    assert statuses[0].last_submitted_at == seeded["ac1"].created_at
    assert statuses[1].status == "Accepted"


def test_get_status_not_attempted(seeded):
    statuses = seeded["service"].get_status(seeded["teacher"].id, seeded["exam"].id)

    assert statuses[0].status == "Not Attempted"
    assert statuses[0].current_score == 0


def test_monitor_aggregates_scores(seeded):
    result = seeded["service"].monitor("teacher", seeded["exam"].id)

    assert result.exam_title == "期中考试"
    assert len(result.problems) == 2
    # alice 200 分排第一，bob 0 分
    assert [entry.user_id for entry in result.users] == [
        seeded["alice"].id,
        seeded["bob"].id,
    ]
    alice_entry = result.users[0]
    assert alice_entry.total_score == 200
    assert alice_entry.submissions[seeded["p1"].id].submission_id == seeded["ac1"].id
    assert alice_entry.submissions[seeded["p2"].id].submission_id == seeded["ac2"].id
    assert result.users[1].total_score == 0


def test_score_rows_matches_manual_expectation(seeded):
    detail, rows = seeded["service"].score_rows("teacher", seeded["exam"].id)

    assert [problem.problem_id for problem in detail.problems] == [
        seeded["p1"].id,
        seeded["p2"].id,
    ]
    by_user = {row.user_id: row for row in rows}
    assert by_user[seeded["alice"].id].scores == [100.0, 100.0]
    assert by_user[seeded["alice"].id].total_score == 200.0
    assert by_user[seeded["bob"].id].scores == [0.0, 0.0]
    assert by_user[seeded["bob"].id].total_score == 0.0


def test_rank_keeps_ac_and_penalty_semantics(seeded):
    result = seeded["service"].rank(seeded["exam"].id)

    assert result.exam_title == "期中考试"
    # 仅 alice 与 bob 有非 Pending 提交
    assert len(result.rank) == 2
    alice_entry = result.rank[0]
    assert alice_entry.solved == 2
    # ac1 在第 300 秒 AC（此前有 1 次 WA，罚时 1200 秒）、ac2 在第 600 秒 AC
    assert alice_entry.penalty == 2100
    assert alice_entry.problems[seeded["p1"].id].solved is True
    assert alice_entry.problems[seeded["p1"].id].time == 300

    bob_entry = result.rank[1]
    assert bob_entry.solved == 0
    assert bob_entry.problems[seeded["p1"].id].failed_attempts == 1


def test_list_exams_uses_batch_counts(seeded):
    items = seeded["service"].list_exams("teacher")

    assert len(items) == 1
    assert items[0].problem_count == 2
    assert items[0].submission_count == 4

"""考试服务批量查询与 N+1 修复回归测试。"""

from datetime import datetime, timedelta

import app.persistence  # noqa: F401
import pytest
from app.persistence.database import Base
from app.persistence.exam import Exam, ExamProblem, ExamRepository
from app.persistence.problem import Problem
from app.persistence.submission import Submission
from app.persistence.unit_of_work import UnitOfWork
from app.persistence.user import User
from app.core.errors import InvalidStateError
from app.services.exam import (
    AddExamProblemParams,
    CreateExamParams,
    EnterExamParams,
    ExamService,
    UpdateExamParams,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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

    service = ExamService(ExamRepository(session), uow=UnitOfWork(session))
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

    assert latest[(seeded["alice"].id, seeded["p1"].id)].id == seeded["ac1"].id
    assert latest[(seeded["alice"].id, seeded["p2"].id)].id == seeded["ac2"].id
    assert latest[(seeded["bob"].id, seeded["p1"].id)].id == seeded["wa_bob"].id
    assert len(latest) == 3


def test_list_latest_submissions_respects_filters(seeded):
    latest = seeded["repository"].list_latest_submissions(
        seeded["exam"].id,
        user_ids=[seeded["bob"].id],
        problem_ids=[seeded["p1"].id],
    )

    assert {key: row.id for key, row in latest.items()} == {
        (seeded["bob"].id, seeded["p1"].id): seeded["wa_bob"].id
    }


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
    result = seeded["service"].rank(seeded["exam"].id, "teacher", -1)

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


@pytest.fixture()
def rank_cache(monkeypatch):
    """用内存缓存验证业务写入后不会继续返回旧排行榜。"""
    cache = {}
    monkeypatch.setattr("app.services.exam.get_rank_cache", cache.get)
    monkeypatch.setattr("app.services.exam.set_rank_cache", cache.__setitem__)
    monkeypatch.setattr(
        "app.services.exam.invalidate_rank_cache", lambda exam_id: cache.pop(exam_id, None)
    )
    return cache


def test_update_exam_refreshes_cached_rank(seeded, rank_cache):
    service, exam_id = seeded["service"], seeded["exam"].id
    service.rank(exam_id, "teacher", -1)

    service.update_exam("teacher", exam_id, UpdateExamParams(title="新考试标题"))

    assert service.rank(exam_id, "teacher", -1).exam_title == "新考试标题"


def test_remove_problem_refreshes_cached_rank(seeded, rank_cache):
    service, exam_id = seeded["service"], seeded["exam"].id
    service.rank(exam_id, "teacher", -1)

    service.remove_problem("teacher", exam_id, seeded["p2"].id)

    result = service.rank(exam_id, "teacher", -1)
    assert [item.problem_id for item in result.problems] == [seeded["p1"].id]
    assert result.rank[0].solved == 1
    assert result.rank[0].penalty == 1500


def test_add_problem_refreshes_cached_rank(seeded, rank_cache):
    service, exam_id = seeded["service"], seeded["exam"].id
    service.remove_problem("teacher", exam_id, seeded["p2"].id)
    service.rank(exam_id, "teacher", -1)

    service.add_problem(
        "teacher", exam_id, AddExamProblemParams(seeded["p2"].id, "B", 100)
    )

    result = service.rank(exam_id, "teacher", -1)
    assert len(result.problems) == 2
    assert result.rank[0].solved == 2
    assert result.rank[0].penalty == 2100


def test_delete_exam_invalidates_cached_rank(seeded, rank_cache):
    service, exam_id = seeded["service"], seeded["exam"].id
    service.rank(exam_id, "teacher", -1)
    assert exam_id in rank_cache

    service.delete_exam("teacher", exam_id)

    assert exam_id not in rank_cache


def test_failed_exam_update_preserves_rank_cache(seeded, rank_cache, monkeypatch):
    service, exam_id = seeded["service"], seeded["exam"].id
    service.rank(exam_id, "teacher", -1)

    def fail_commit():
        raise RuntimeError("提交失败")

    monkeypatch.setattr(service._uow, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="提交失败"):
        service.update_exam("teacher", exam_id, UpdateExamParams(title="新考试标题"))

    assert rank_cache[exam_id]["exam_title"] == "期中考试"


def test_latest_submission_breaks_timestamp_ties_by_id(seeded):
    """同一时间戳的后续提交必须覆盖旧提交，状态与成绩导出保持一致。"""
    session = seeded["session"]
    old = seeded["ac1"]
    newer = Submission(
        user_id=old.user_id,
        problem_id=old.problem_id,
        exam_id=old.exam_id,
        status="Wrong Answer",
        score=0,
        created_at=old.created_at,
    )
    session.add(newer)
    session.commit()

    repository = seeded["repository"]
    latest = repository.list_latest_submissions(old.exam_id)
    assert latest[(old.user_id, old.problem_id)].id == newer.id
    assert (
        repository.get_latest_submission(old.exam_id, old.user_id, old.problem_id).id
        == newer.id
    )

    statuses = seeded["service"].get_status(old.user_id, old.exam_id)
    assert statuses[0].status == "Wrong Answer"
    _, rows = seeded["service"].score_rows("teacher", old.exam_id)
    alice_row = next(row for row in rows if row.user_id == old.user_id)
    assert alice_row.scores == [0.0, 100.0]


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-01-01T17:00:00+08:00", "2026-01-01T06:00:00-05:00"),
        ("2026-01-01T17:00:00+08:00", "2026-01-01T11:00:00"),
        ("2026-01-01T09:00:00", "2026-01-01T19:00:00+08:00"),
    ],
)
def test_create_exam_normalizes_timezones_before_validation_and_storage(
    seeded, monkeypatch, start, end
):
    service = seeded["service"]
    detail = service.create_exam(
        "teacher",
        CreateExamParams(
            title="带时区考试",
            description="",
            start_time=datetime.fromisoformat(start),
            end_time=datetime.fromisoformat(end),
            created_by=seeded["teacher"].id,
            is_visible=True,
        ),
    )
    assert detail.start_time == T0
    assert detail.end_time == T0 + timedelta(hours=2)
    stored = seeded["repository"].get_by_id(detail.id)
    assert stored.start_time == T0
    assert stored.end_time == T0 + timedelta(hours=2)
    monkeypatch.setattr("app.services.exam.utcnow", lambda: T0 + timedelta(minutes=30))
    assert (
        service.enter_exam("student", seeded["alice"].id, -1, EnterExamParams(detail.id))
        == detail.id
    )


@pytest.mark.parametrize(
    "params,expected_start,expected_end",
    [
        (
            UpdateExamParams(start_time=datetime.fromisoformat("2026-01-01T18:00:00+08:00")),
            T0 + timedelta(hours=1),
            T0 + timedelta(hours=2),
        ),
        (
            UpdateExamParams(end_time=datetime.fromisoformat("2026-01-01T20:00:00+08:00")),
            T0,
            T0 + timedelta(hours=3),
        ),
    ],
)
def test_partial_exam_update_accepts_timezone(seeded, params, expected_start, expected_end):
    detail = seeded["service"].update_exam("teacher", seeded["exam"].id, params)
    assert detail.start_time == expected_start
    assert detail.end_time == expected_end
    stored = seeded["repository"].get_by_id(detail.id)
    assert stored.start_time == expected_start
    assert stored.end_time == expected_end


@pytest.mark.parametrize("end", ["2026-01-01T09:00:00", "2026-01-01T08:00:00Z"])
def test_timezone_update_rejects_equal_or_reversed_times_without_persisting(seeded, end):
    exam_id = seeded["exam"].id
    with pytest.raises(InvalidStateError, match="考试开始时间必须早于结束时间"):
        seeded["service"].update_exam(
            "teacher", exam_id, UpdateExamParams(end_time=datetime.fromisoformat(end))
        )
    stored = seeded["repository"].get_by_id(exam_id)
    assert stored.start_time == T0
    assert stored.end_time == T0 + timedelta(hours=2)


def test_disabling_freeze_persists_and_refreshes_rank(seeded, rank_cache):
    """关闭封榜后，既清空持久化设置，也立即重算已有缓存中的罚时。"""
    service, exam_id = seeded["service"], seeded["exam"].id
    service.update_exam("teacher", exam_id, UpdateExamParams(freeze_minutes=30))
    service.rank(exam_id, "teacher", -1)
    assert exam_id in rank_cache

    updated = service.update_exam(
        "teacher", exam_id, UpdateExamParams(clear_freeze_minutes=True)
    )

    assert updated.freeze_minutes is None
    assert seeded["repository"].get_by_id(exam_id).freeze_minutes is None
    assert exam_id not in rank_cache
    assert service.rank(exam_id, "teacher", -1).rank[0].penalty == 2100


@pytest.mark.parametrize("offset", [5400, 6000, 7200, 7300])
def test_freeze_preserves_pre_freeze_results_and_penalties(seeded, offset):
    exam = seeded["exam"]
    exam.freeze_minutes = 30
    seeded["session"].commit()
    result = seeded["service"].rank(
        exam.id, "teacher", -1, as_of=(T0 + timedelta(seconds=offset)).isoformat()
    )
    alice = next(entry for entry in result.rank if entry.user_id == seeded["alice"].id)
    assert alice.solved == 2
    assert alice.penalty == 2100
    assert alice.problems[seeded["p1"].id].failed_attempts == 1


def test_freeze_hides_late_acceptance_and_unfreezes_at_exam_end(seeded, rank_cache, monkeypatch):
    exam = seeded["exam"]
    exam.freeze_minutes = 30
    session = seeded["session"]
    session.add(Submission(
        user_id=seeded["bob"].id, problem_id=seeded["p1"].id, exam_id=exam.id,
        status="Accepted", score=100, created_at=T0 + timedelta(seconds=6000),
    ))
    session.commit()

    def bob_entry(result):
        return next(entry for entry in result.rank if entry.user_id == seeded["bob"].id)

    monkeypatch.setattr("app.services.exam.utcnow", lambda: T0 + timedelta(seconds=5399))
    before = bob_entry(seeded["service"].rank(exam.id, "teacher", -1))
    assert before.solved == 0
    assert before.problems[seeded["p1"].id].pending_attempts == 0
    monkeypatch.setattr("app.services.exam.utcnow", lambda: T0 + timedelta(seconds=6000))
    frozen = bob_entry(seeded["service"].rank(exam.id, "teacher", -1))
    assert frozen.solved == 0
    assert frozen.problems[seeded["p1"].id].pending_attempts == 1
    assert frozen.problems[seeded["p1"].id].failed_attempts == 1
    # 再读缓存也必须保留封榜状态。
    assert bob_entry(seeded["service"].rank(exam.id, "teacher", -1)) == frozen

    monkeypatch.setattr("app.services.exam.utcnow", lambda: T0 + timedelta(seconds=7200))
    final = bob_entry(seeded["service"].rank(exam.id, "teacher", -1))
    assert final.solved == 1
    assert final.penalty == 7200
    assert final.problems[seeded["p1"].id].pending_attempts == 0


def test_future_rank_timestamp_cannot_bypass_current_freeze(seeded, monkeypatch):
    exam = seeded["exam"]
    exam.freeze_minutes = 30
    seeded["session"].add(Submission(
        user_id=seeded["bob"].id, problem_id=seeded["p1"].id, exam_id=exam.id,
        status="Accepted", score=100, created_at=T0 + timedelta(seconds=6000),
    ))
    seeded["session"].commit()
    monkeypatch.setattr("app.services.exam.utcnow", lambda: T0 + timedelta(seconds=6100))
    result = seeded["service"].rank(
        exam.id, "student", exam.id, as_of=(T0 + timedelta(seconds=8000)).isoformat()
    )
    bob = next(entry for entry in result.rank if entry.user_id == seeded["bob"].id)
    assert bob.solved == 0


@pytest.mark.parametrize("contest_type,freeze_minutes", [("icpc", 0), ("ioi", 30)])
def test_freeze_does_not_apply_when_disabled_or_not_icpc(seeded, contest_type, freeze_minutes):
    exam = seeded["exam"]
    exam.contest_type, exam.freeze_minutes = contest_type, freeze_minutes
    seeded["session"].add(Submission(
        user_id=seeded["bob"].id, problem_id=seeded["p1"].id, exam_id=exam.id,
        status="Accepted", score=100, created_at=T0 + timedelta(seconds=6000),
    ))
    seeded["session"].commit()
    result = seeded["service"].rank(
        exam.id, "teacher", -1, as_of=(T0 + timedelta(seconds=6000)).isoformat()
    )
    bob = next(entry for entry in result.rank if entry.user_id == seeded["bob"].id)
    assert bob.problems[seeded["p1"].id].solved is True
    assert bob.problems[seeded["p1"].id].pending_attempts == 0


def test_rank_api_returns_frozen_pending_attempts(seeded, client, teacher_token, monkeypatch):
    from app.api.deps import get_exam_service

    exam = seeded["exam"]
    exam.freeze_minutes = 30
    seeded["session"].add(Submission(
        user_id=seeded["bob"].id, problem_id=seeded["p1"].id, exam_id=exam.id,
        status="Accepted", score=100, created_at=T0 + timedelta(seconds=6000),
    ))
    seeded["session"].commit()
    monkeypatch.setattr("app.services.exam.utcnow", lambda: T0 + timedelta(seconds=6100))
    client.app.dependency_overrides[get_exam_service] = lambda: seeded["service"]

    response = client.get(
        f"/api/exams/{exam.id}/rank", headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert response.status_code == 200
    bob = next(entry for entry in response.json()["rank"] if entry["user_id"] == seeded["bob"].id)
    assert bob["solved"] == 0
    assert bob["problems"][str(seeded["p1"].id)]["pending_attempts"] == 1

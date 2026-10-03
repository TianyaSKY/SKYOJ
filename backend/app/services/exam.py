"""exam 业务参数、结果与服务。"""

from __future__ import annotations

import hashlib
from app.core.config import SECRET_KEY
from app.core.errors import (
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.core.time import utcnow
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from loguru import logger
from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from app.services.problem import ProblemRecord


@dataclass(frozen=True)
class CreateExamParams:
    """创建考试参数。"""

    title: str
    description: str
    start_time: datetime
    end_time: datetime
    contest_type: str = "icpc"
    freeze_minutes: Optional[int] = None
    password: Optional[str] = None
    is_visible: bool = False
    created_by: int = 0


@dataclass(frozen=True)
class UpdateExamParams:
    """更新考试参数。"""

    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    contest_type: Optional[str] = None
    freeze_minutes: Optional[int] = None
    password: Optional[str] = None
    is_visible: Optional[bool] = None


@dataclass(frozen=True)
class EnterExamParams:
    """进入考试参数。"""

    exam_id: int
    password: Optional[str] = None


@dataclass(frozen=True)
class AddExamProblemParams:
    """向考试添加题目的业务参数。"""

    problem_id: int
    display_id: Optional[str] = None
    score: int = 100


@dataclass(frozen=True)
class ExamProblemItem:
    """考试题目信息。"""

    problem_id: int
    display_id: Optional[str]
    score: int
    title: str


@dataclass(frozen=True)
class ExamListItem:
    """考试列表项。"""

    id: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    contest_type: str
    freeze_minutes: Optional[int]
    is_visible: bool
    created_by: int
    problem_count: int
    submission_count: int
    has_password: bool


@dataclass(frozen=True)
class ExamDetail:
    """考试详情。"""

    id: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    contest_type: str
    freeze_minutes: Optional[int]
    is_visible: bool
    created_by: int
    has_password: bool
    problems: list[ExamProblemItem]


@dataclass(frozen=True)
class ExamProblemStatus:
    """考试题目状态（当前学生在考试中的每题状态）。"""

    problem_id: int
    display_id: Optional[str]
    title: str
    max_score: int
    status: str
    current_score: float
    last_submitted_at: Optional[datetime]


@dataclass(frozen=True)
class MonitorSubmissionInfo:
    """监控页单次提交信息。"""

    submission_id: Optional[int]
    status: str
    score: float
    time: Optional[str]


@dataclass(frozen=True)
class MonitorProblemInfo:
    """监控页题目头部信息。"""

    problem_id: int
    display_id: Optional[str]
    max_score: int


@dataclass(frozen=True)
class MonitorEntry:
    """监控页单个用户条目。"""

    user_id: int
    username: str
    total_score: float
    submissions: dict[int, MonitorSubmissionInfo]


@dataclass(frozen=True)
class MonitorResult:
    """监控页结果。"""

    exam_title: str
    problems: list[MonitorProblemInfo]
    users: list[MonitorEntry]


@dataclass(frozen=True)
class RankProblemStats:
    """排行榜中单题统计。"""

    solved: bool
    failed_attempts: int
    time: int


@dataclass(frozen=True)
class RankProblemInfo:
    """排行榜题目头部信息。"""

    problem_id: int
    display_id: Optional[str]


@dataclass(frozen=True)
class RankEntry:
    """排行榜单个用户条目。"""

    user_id: int
    username: str
    solved: int
    penalty: int
    problems: dict[int, RankProblemStats]


@dataclass(frozen=True)
class RankResult:
    """排行榜结果。"""

    exam_title: str
    problems: list[RankProblemInfo]
    rank: list[RankEntry]

    def to_dict(self) -> dict:
        return {
            "exam_title": self.exam_title,
            "problems": [
                {"problem_id": p.problem_id, "display_id": p.display_id}
                for p in self.problems
            ],
            "rank": [
                {
                    "user_id": e.user_id,
                    "username": e.username,
                    "solved": e.solved,
                    "penalty": e.penalty,
                    "problems": {
                        str(pid): {
                            "solved": stats.solved,
                            "failed_attempts": stats.failed_attempts,
                            "time": stats.time,
                        }
                        for pid, stats in e.problems.items()
                    },
                }
                for e in self.rank
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RankResult":
        return cls(
            exam_title=data["exam_title"],
            problems=[
                RankProblemInfo(p["problem_id"], p.get("display_id"))
                for p in data.get("problems", [])
            ],
            rank=[
                RankEntry(
                    user_id=e["user_id"],
                    username=e["username"],
                    solved=e["solved"],
                    penalty=e["penalty"],
                    problems={
                        int(pid): RankProblemStats(
                            solved=stats["solved"],
                            failed_attempts=stats["failed_attempts"],
                            time=stats["time"],
                        )
                        for pid, stats in e.get("problems", {}).items()
                    },
                )
                for e in data.get("rank", [])
            ],
        )


@dataclass(frozen=True)
class ExamScoreRow:
    """导出成绩时单个学生的一行数据。"""

    user_id: int
    username: str
    scores: list[float]
    total_score: float


@dataclass
class ExamRecord:
    """Exam 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    title: str
    description: str | None
    start_time: datetime
    end_time: datetime
    contest_type: str
    freeze_minutes: int | None
    password: str | None
    is_visible: bool | None
    created_by: int | None


@dataclass
class ExamProblemRecord:
    """ExamProblem 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    exam_id: int
    problem_id: int
    display_id: str | None
    score: int | None
    problem: ProblemRecord | None


from app.persistence.exam import ExamRepository, to_exam_detail, to_exam_list_item


class ExamService:
    """编排考试管理、考试状态和成绩统计业务。"""

    def __init__(self, repository: ExamRepository) -> None:
        self._repository = repository

    def create_exam(self, requester_role: str, params: CreateExamParams) -> ExamDetail:
        self._require_teacher(requester_role)
        self._validate_times(params.start_time, params.end_time)
        exam = self._repository.create(
            title=params.title,
            description=params.description,
            start_time=params.start_time,
            end_time=params.end_time,
            contest_type=params.contest_type,
            freeze_minutes=params.freeze_minutes,
            password=self._hash_password(params.password),
            is_visible=params.is_visible,
            created_by=params.created_by,
        )
        self._repository.unit_of_work.commit()
        return to_exam_detail(exam, [])

    def list_exams(self, requester_role: str) -> list[ExamListItem]:
        exams = self._repository.list_visible_for(requester_role)
        exam_ids = [exam.id for exam in exams]
        problem_counts = self._repository.count_problems_batch(exam_ids)
        submission_counts = self._repository.count_submissions_batch(exam_ids)
        return [
            to_exam_list_item(
                exam,
                problem_count=problem_counts.get(exam.id, 0),
                submission_count=submission_counts.get(exam.id, 0),
            )
            for exam in exams
        ]

    def get_detail(
        self, exam_id: int, requester_role: str, session_exam_id: int
    ) -> ExamDetail:
        exam = self._require_exam(exam_id)
        self._assert_exam_discoverable(requester_role, exam, session_exam_id)
        if self._should_hide_problems(requester_role, exam, session_exam_id):
            return to_exam_detail(exam, [])
        return to_exam_detail(exam, self._repository.list_problems(exam_id))

    def enter_exam(
        self,
        requester_role: str,
        user_id: int,
        current_exam_id: int,
        params: EnterExamParams,
    ) -> int:
        del user_id
        exam = self._require_exam(params.exam_id)
        self._assert_exam_discoverable(requester_role, exam, current_exam_id)
        now = utcnow()
        if now < exam.start_time:
            raise PermissionDeniedError("考试尚未开始")
        if now > exam.end_time:
            raise PermissionDeniedError("考试已结束")
        if (
            current_exam_id != exam.id
            and exam.password
            and self._hash_password(params.password) != exam.password
        ):
            raise PermissionDeniedError("考试密码错误")
        return exam.id

    def get_status(self, user_id: int, exam_id: int) -> list[ExamProblemStatus]:
        if exam_id == -1:
            raise InvalidStateError("当前未处于考试会话")
        problems = self._repository.list_problems(exam_id)
        latest = self._repository.list_latest_submissions(
            exam_id,
            user_ids=[user_id],
            problem_ids=[item.problem_id for item in problems],
        )
        items = []
        for item in problems:
            last = latest.get((user_id, item.problem_id))
            items.append(
                ExamProblemStatus(
                    item.problem_id,
                    item.display_id,
                    item.problem.title,
                    item.score,
                    last.status if last else "Not Attempted",
                    last.score if last else 0,
                    last.created_at if last else None,
                )
            )
        return items

    def update_exam(
        self, requester_role: str, exam_id: int, params: UpdateExamParams
    ) -> ExamDetail:
        self._require_teacher(requester_role)
        exam = self._require_exam(exam_id)
        start_time = (
            params.start_time if params.start_time is not None else exam.start_time
        )
        end_time = params.end_time if params.end_time is not None else exam.end_time
        self._validate_times(start_time, end_time)
        for field, value in (
            ("title", params.title),
            ("description", params.description),
            ("start_time", params.start_time),
            ("end_time", params.end_time),
            ("is_visible", params.is_visible),
            ("contest_type", params.contest_type),
            ("freeze_minutes", params.freeze_minutes),
        ):
            if value is not None:
                setattr(exam, field, value)
        if params.password is not None:
            exam.password = self._hash_password(params.password)
        self._repository.update(exam)
        self._repository.unit_of_work.commit()
        return to_exam_detail(exam, self._repository.list_problems(exam_id))

    def delete_exam(self, requester_role: str, exam_id: int) -> None:
        self._require_teacher(requester_role)
        self._repository.delete(self._require_exam(exam_id))
        self._repository.unit_of_work.commit()

    def add_problem(
        self, requester_role: str, exam_id: int, params: AddExamProblemParams
    ) -> None:
        self._require_teacher(requester_role)
        self._require_exam(exam_id)
        self._repository.add_problem(
            exam_id, params.problem_id, params.display_id, params.score
        )
        self._repository.unit_of_work.commit()

    def remove_problem(
        self, requester_role: str, exam_id: int, problem_id: int
    ) -> None:
        self._require_teacher(requester_role)
        item = self._repository.get_exam_problem(exam_id, problem_id)
        if item is None:
            raise ResourceNotFoundError("考试题目不存在")
        self._repository.delete_exam_problem(item)
        self._repository.unit_of_work.commit()

    def monitor(self, requester_role: str, exam_id: int) -> MonitorResult:
        self._require_teacher(requester_role)
        exam = self._require_exam(exam_id)
        problems = self._repository.list_problems(exam_id)
        problem_ids = [item.problem_id for item in problems]
        user_ids = self._repository.list_submission_user_ids(exam_id)
        users_map = self._repository.list_users(user_ids)
        latest = self._repository.list_latest_submissions(
            exam_id, user_ids=user_ids, problem_ids=problem_ids
        )
        users = []
        for user_id in user_ids:
            user = users_map[user_id]
            submissions, total = {}, 0.0
            for item in problems:
                last = latest.get((user_id, item.problem_id))
                info = MonitorSubmissionInfo(
                    last.id if last else None,
                    last.status if last else "Not Attempted",
                    last.score if last else 0,
                    last.created_at.isoformat() if last else None,
                )
                submissions[item.problem_id] = info
                total += info.score
            users.append(MonitorEntry(user.id, user.username, total, submissions))
        users.sort(key=lambda item: item.total_score, reverse=True)
        return MonitorResult(
            exam.title,
            [
                MonitorProblemInfo(item.problem_id, item.display_id, item.score)
                for item in problems
            ],
            users,
        )

    def rank(
        self,
        exam_id: int,
        requester_role: str,
        session_exam_id: int,
        as_of: str | None = None,
    ) -> RankResult:
        """
        排行榜计算。

        参数:
        - as_of: 可选的时间戳字符串（ISO 格式），用于回溯查看历史排行榜。
          例如 as_of=exam.end_time - freeze_minutes 即可看到封榜前的最后一刻。
          不传时按当前时间计算（实况排行榜）。
        - exam.freeze_minutes: ICPC 比赛结束前 N 分钟封榜。
          封榜期间所有未 Accepted 提交在 scoreboard 上显示为 '?'。
        """
        from app.utils.exam_cache import get_rank_cache, set_rank_cache

        exam = self._require_exam(exam_id)
        self._assert_exam_discoverable(requester_role, exam, session_exam_id)
        if self._should_hide_problems(requester_role, exam, session_exam_id):
            raise PermissionDeniedError("请先进入考试")
        if as_of is None:
            cached = get_rank_cache(exam_id)
            if cached is not None:
                return RankResult.from_dict(cached)

        problems = self._repository.list_problems(exam_id)
        problem_ids = [item.problem_id for item in problems]

        # as_of 决定截断时间：排行榜只统计 as_of 之前的提交。
        now = datetime.utcnow()
        view_time = now
        if as_of is not None:
            try:
                view_time = datetime.fromisoformat(as_of)
                if view_time.tzinfo is not None:
                    view_time = view_time.astimezone(UTC).replace(tzinfo=None)
            except (TypeError, ValueError):
                logger.warning(
                    "排行榜回溯时间无效，使用当前时间 exam_id={} as_of={}",
                    exam_id,
                    as_of,
                )
                view_time = now
        # freeze_minutes: 如果当前视口时间 > (end_time - freeze_minutes)，
        # 则视为处于封榜期，failed_attempts 不计入 scoreboard。
        freeze_end = None
        if exam.freeze_minutes is not None:
            freeze_end = exam.end_time - timedelta(minutes=exam.freeze_minutes)
        in_freeze = freeze_end is not None and view_time >= freeze_end

        ranks: dict[int, RankEntry] = {}
        # 过滤只取 view_time 之前的提交。
        all_submissions = self._repository.list_submissions(exam_id, problem_ids)
        for submission in all_submissions:
            if submission.created_at > view_time:
                continue
            if submission.user_id not in ranks:
                ranks[submission.user_id] = RankEntry(
                    submission.user_id,
                    submission.user.username,
                    0,
                    0,
                    {pid: RankProblemStats(False, 0, 0) for pid in problem_ids},
                )
            entry = ranks[submission.user_id]
            stats = entry.problems.get(submission.problem_id)
            if stats is None or stats.solved:
                continue
            if submission.status == "Accepted":
                elapsed = int((submission.created_at - exam.start_time).total_seconds())
                entry.problems[submission.problem_id] = RankProblemStats(
                    True,
                    stats.failed_attempts if not in_freeze else 0,
                    elapsed,
                )
                ranks[submission.user_id] = RankEntry(
                    entry.user_id,
                    entry.username,
                    entry.solved + 1,
                    entry.penalty
                    + elapsed
                    + (stats.failed_attempts if not in_freeze else 0) * 1200,
                    entry.problems,
                )
            elif submission.status not in {"Pending", "Compile Error"}:
                entry.problems[submission.problem_id] = RankProblemStats(
                    False,
                    stats.failed_attempts + 1
                    if not in_freeze
                    else stats.failed_attempts,
                    0,
                )

        result = RankResult(
            exam.title,
            [RankProblemInfo(item.problem_id, item.display_id) for item in problems],
            sorted(ranks.values(), key=lambda item: (-item.solved, item.penalty)),
        )
        if as_of is None:
            set_rank_cache(exam_id, result.to_dict())
        return result

    def score_rows(
        self, requester_role: str, exam_id: int
    ) -> tuple[ExamDetail, list[ExamScoreRow]]:
        self._require_teacher(requester_role)
        detail = self.get_detail(exam_id, requester_role, -1)
        problem_ids = [problem.problem_id for problem in detail.problems]
        user_ids = self._repository.list_submission_user_ids(exam_id)
        users_map = self._repository.list_users(user_ids)
        latest = self._repository.list_latest_submissions(
            exam_id, user_ids=user_ids, problem_ids=problem_ids
        )
        rows = []
        for user_id in user_ids:
            user = users_map[user_id]
            scores = []
            for problem in detail.problems:
                submission = latest.get((user_id, problem.problem_id))
                scores.append(submission.score if submission else 0)
            rows.append(ExamScoreRow(user.id, user.username, scores, sum(scores)))
        return detail, rows

    def _require_exam(self, exam_id: int) -> ExamRecord:
        exam = self._repository.get_by_id(exam_id)
        if exam is None:
            raise ResourceNotFoundError("考试不存在")
        return exam

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

    @staticmethod
    def _has_exam_session(session_exam_id: int, exam_id: int) -> bool:
        return session_exam_id == exam_id

    def _assert_exam_discoverable(self, role: str, exam, session_exam_id: int) -> None:
        """教师、已入场学生或公开考试可以知道该考试存在。"""
        if role == "teacher" or self._has_exam_session(session_exam_id, exam.id):
            return
        if not exam.is_visible:
            raise ResourceNotFoundError("考试不存在")

    def _should_hide_problems(self, role: str, exam, session_exam_id: int) -> bool:
        """密码考试在入场前不返回题目列表。"""
        if role == "teacher" or self._has_exam_session(session_exam_id, exam.id):
            return False
        return bool(exam.password)

    @staticmethod
    def _validate_times(start_time: datetime, end_time: datetime) -> None:
        if start_time >= end_time:
            raise InvalidStateError("考试开始时间必须早于结束时间")

    @staticmethod
    def _hash_password(password: str | None) -> str | None:
        return (
            hashlib.sha256((password + SECRET_KEY).encode()).hexdigest()
            if password
            else None
        )

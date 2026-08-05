"""考试领域业务服务。"""

import hashlib
from datetime import datetime

from app.config import SECRET_KEY
from app.domain.errors import InvalidStateError, PermissionDeniedError, ResourceNotFoundError
from app.domain.exam import (
    AddExamProblemParams, CreateExamParams, EnterExamParams, ExamDetail, ExamListItem,
    ExamProblemStatus, ExamScoreRow, MonitorEntry, MonitorProblemInfo,
    MonitorResult, MonitorSubmissionInfo, RankEntry, RankProblemInfo, RankProblemStats,
    RankResult, UpdateExamParams,
)
from app.mappers import from_exam_detail_orm, from_exam_orm
from app.repositories.exam_repository import ExamRepository


class ExamService:
    """编排考试管理、考试状态和成绩统计业务。"""

    def __init__(self, repository: ExamRepository) -> None:
        self._repository = repository

    def create_exam(self, requester_role: str, params: CreateExamParams) -> ExamDetail:
        self._require_teacher(requester_role)
        self._validate_times(params.start_time, params.end_time)
        exam = self._repository.create(title=params.title, description=params.description, start_time=params.start_time, end_time=params.end_time, password=self._hash_password(params.password), is_visible=params.is_visible, created_by=params.created_by)
        return from_exam_detail_orm(exam, [])

    def list_exams(self, requester_role: str) -> list[ExamListItem]:
        exams = self._repository.list_visible_for(requester_role)
        exam_ids = [exam.id for exam in exams]
        problem_counts = self._repository.count_problems_batch(exam_ids)
        submission_counts = self._repository.count_submissions_batch(exam_ids)
        return [
            from_exam_orm(
                exam,
                problem_count=problem_counts.get(exam.id, 0),
                submission_count=submission_counts.get(exam.id, 0),
            )
            for exam in exams
        ]

    def get_detail(self, exam_id: int) -> ExamDetail:
        exam = self._require_exam(exam_id)
        return from_exam_detail_orm(exam, self._repository.list_problems(exam_id))

    def enter_exam(self, user_id: int, current_exam_id: int, params: EnterExamParams) -> int:
        exam = self._require_exam(params.exam_id)
        now = datetime.utcnow()
        if now < exam.start_time:
            raise PermissionDeniedError("考试尚未开始")
        if now > exam.end_time:
            raise PermissionDeniedError("考试已结束")
        if current_exam_id != exam.id and exam.password and self._hash_password(params.password) != exam.password:
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
            items.append(ExamProblemStatus(item.problem_id, item.display_id, item.problem.title, item.score, last.status if last else "Not Attempted", last.score if last else 0, last.created_at if last else None))
        return items

    def update_exam(self, requester_role: str, exam_id: int, params: UpdateExamParams) -> ExamDetail:
        self._require_teacher(requester_role)
        exam = self._require_exam(exam_id)
        start_time = params.start_time if params.start_time is not None else exam.start_time
        end_time = params.end_time if params.end_time is not None else exam.end_time
        self._validate_times(start_time, end_time)
        for field, value in (("title", params.title), ("description", params.description), ("start_time", params.start_time), ("end_time", params.end_time), ("is_visible", params.is_visible)):
            if value is not None:
                setattr(exam, field, value)
        if params.password is not None:
            exam.password = self._hash_password(params.password)
        return from_exam_detail_orm(self._repository.update(exam), self._repository.list_problems(exam_id))

    def delete_exam(self, requester_role: str, exam_id: int) -> None:
        self._require_teacher(requester_role)
        self._repository.delete(self._require_exam(exam_id))

    def add_problem(self, requester_role: str, exam_id: int, params: AddExamProblemParams) -> None:
        self._require_teacher(requester_role)
        self._require_exam(exam_id)
        self._repository.add_problem(exam_id, params.problem_id, params.display_id, params.score)

    def remove_problem(self, requester_role: str, exam_id: int, problem_id: int) -> None:
        self._require_teacher(requester_role)
        item = self._repository.get_exam_problem(exam_id, problem_id)
        if item is None:
            raise ResourceNotFoundError("考试题目不存在")
        self._repository.delete_exam_problem(item)

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
                info = MonitorSubmissionInfo(last.id if last else None, last.status if last else "Not Attempted", last.score if last else 0, last.created_at.isoformat() if last else None)
                submissions[item.problem_id] = info
                total += info.score
            users.append(MonitorEntry(user.id, user.username, total, submissions))
        users.sort(key=lambda item: item.total_score, reverse=True)
        return MonitorResult(exam.title, [MonitorProblemInfo(item.problem_id, item.display_id, item.score) for item in problems], users)

    def rank(self, exam_id: int) -> RankResult:
        exam = self._require_exam(exam_id)
        problems = self._repository.list_problems(exam_id)
        problem_ids = [item.problem_id for item in problems]
        ranks: dict[int, RankEntry] = {}
        for submission in self._repository.list_submissions(exam_id, problem_ids):
            if submission.user_id not in ranks:
                ranks[submission.user_id] = RankEntry(submission.user_id, submission.user.username, 0, 0, {pid: RankProblemStats(False, 0, 0) for pid in problem_ids})
            entry = ranks[submission.user_id]
            stats = entry.problems.get(submission.problem_id)
            if stats is None or stats.solved:
                continue
            if submission.status == "Accepted":
                elapsed = int((submission.created_at - exam.start_time).total_seconds())
                entry.problems[submission.problem_id] = RankProblemStats(True, stats.failed_attempts, elapsed)
                ranks[submission.user_id] = RankEntry(entry.user_id, entry.username, entry.solved + 1, entry.penalty + elapsed + stats.failed_attempts * 1200, entry.problems)
            elif submission.status not in {"Pending", "Compile Error"}:
                entry.problems[submission.problem_id] = RankProblemStats(False, stats.failed_attempts + 1, 0)
        return RankResult(exam.title, [RankProblemInfo(item.problem_id, item.display_id) for item in problems], sorted(ranks.values(), key=lambda item: (-item.solved, item.penalty)))

    def score_rows(self, requester_role: str, exam_id: int) -> tuple[ExamDetail, list[ExamScoreRow]]:
        self._require_teacher(requester_role)
        detail = self.get_detail(exam_id)
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

    def _require_exam(self, exam_id: int):
        exam = self._repository.get_by_id(exam_id)
        if exam is None:
            raise ResourceNotFoundError("考试不存在")
        return exam

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("没有教师权限")

    @staticmethod
    def _validate_times(start_time: datetime, end_time: datetime) -> None:
        if start_time >= end_time:
            raise InvalidStateError("考试开始时间必须早于结束时间")

    @staticmethod
    def _hash_password(password: str | None) -> str | None:
        return hashlib.sha256((password + SECRET_KEY).encode()).hexdigest() if password else None

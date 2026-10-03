"""wrong_book 业务参数、结果与服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from loguru import logger

from app.core.errors import ResourceNotFoundError
from app.core.time import utcnow
from app.persistence.unit_of_work import UnitOfWork
from app.persistence.user import WrongBookRepository


@dataclass(frozen=True)
class WrongBookItem:
    """错题列表项（学生视角）。"""

    id: int
    problem_id: int
    problem_title: str
    submission_id: Optional[int]
    first_wrong_at: Optional[datetime]
    latest_wrong_at: Optional[datetime]
    accepted: bool
    reviewed: bool


@dataclass(frozen=True)
class WrongBookStats:
    """错题本统计。"""

    total: int
    unresolved: int
    reviewed: int
    accepted: int


@dataclass(frozen=True)
class ToggleReviewedResult:
    """标记/取消标记已复习。"""

    id: int
    reviewed: bool


# 视为"错题"的状态列表。
_WRONG_STATUSES = {
    "Wrong Answer",
    "Time Limit Exceeded",
    "Runtime Error",
    "System Error",
}


class WrongBookService:
    def __init__(self, repository: WrongBookRepository, *, uow: UnitOfWork) -> None:
        self._uow = uow
        self._repo = repository

    # === 判题结果监听 ===

    def on_judge_complete(
        self,
        user_id: int,
        problem_id: int,
        submission_id: int,
        status: str,
    ) -> None:
        """由 judge_service 在判题完成后调用，写入/更新错题本。"""
        with self._uow.transaction():
            self.record_judge_result(user_id, problem_id, submission_id, status)

    def record_judge_result(
        self, user_id: int, problem_id: int, submission_id: int, status: str
    ) -> None:
        """写入判题结果对应的错题状态，由调用方统一提交。"""
        if status != "Accepted" and status not in _WRONG_STATUSES:
            return
        if self._repo.has_newer_judged_submission(
            user_id, problem_id, submission_id, ("Accepted", *sorted(_WRONG_STATUSES))
        ):
            logger.info(
                "已有更新提交的判题结果，跳过旧错题状态更新 user_id={} problem_id={} submission_id={}",
                user_id, problem_id, submission_id,
            )
            return
        now = utcnow()
        if status == "Accepted":
            self._repo.mark_accepted(user_id, problem_id)
        elif status in _WRONG_STATUSES:
            self._repo.upsert(
                user_id=user_id,
                problem_id=problem_id,
                submission_id=submission_id,
                now=now,
            )
        # Pending / Compile Error 不操作。

    # === 查询 ===

    def list_for_user(
        self,
        user_id: int,
        *,
        unresolved_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WrongBookItem], int]:
        rows, total = self._repo.list_for_user(
            user_id, unresolved_only=unresolved_only, page=page, page_size=page_size
        )
        items = [
            WrongBookItem(
                id=row.id,
                problem_id=row.problem_id,
                problem_title=row.problem.title if row.problem else "Unknown",
                submission_id=row.submission_id,
                first_wrong_at=row.first_wrong_at,
                latest_wrong_at=row.latest_wrong_at,
                accepted=row.accepted,
                reviewed=row.reviewed,
            )
            for row in rows
        ]
        return items, total

    def get_stats(self, user_id: int) -> WrongBookStats:
        total, unresolved, reviewed, accepted = self._repo.get_stats(user_id)
        return WrongBookStats(
            total=total, unresolved=unresolved, reviewed=reviewed, accepted=accepted
        )

    def toggle_reviewed(self, entry_id: int, requester_id: int) -> ToggleReviewedResult:
        """切换复习标记。"""
        with self._uow.transaction():
            row = self._repo.get_by_id(entry_id)
            if row is None:
                raise ResourceNotFoundError("错题记录不存在")
            if row.user_id != requester_id:
                from app.core.errors import PermissionDeniedError

                raise PermissionDeniedError("无权修改此记录")
            row = self._repo.toggle_reviewed(entry_id)
            return ToggleReviewedResult(id=row.id, reviewed=row.reviewed)

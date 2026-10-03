"""wrong_book 业务参数、结果与服务。"""

from __future__ import annotations

from app.core.errors import ResourceNotFoundError
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional


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
_WRONG_STATUSES = {"Wrong Answer", "Time Limit Exceeded", "Runtime Error", "System Error"}


from app.persistence.user import WrongBookRepository


class WrongBookService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = WrongBookRepository(db)

    # === 判题结果监听 ===

    def on_judge_complete(
        self,
        user_id: int,
        problem_id: int,
        submission_id: int,
        status: str,
    ) -> None:
        """由 judge_service 在判题完成后调用，写入/更新错题本。"""
        now = datetime.utcnow()
        if status == "Accepted":
            self._repo.mark_accepted(user_id, problem_id)
            self._db.commit()
        elif status in _WRONG_STATUSES:
            self._repo.upsert(
                user_id=user_id,
                problem_id=problem_id,
                submission_id=submission_id,
                now=now,
            )
            self._db.commit()
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
        row = self._repo.toggle_reviewed(entry_id)
        if row is None:
            raise ResourceNotFoundError("错题记录不存在")
        if row.user_id != requester_id:
            from app.core.errors import PermissionDeniedError

            raise PermissionDeniedError("无权修改此记录")
        self._db.commit()
        return ToggleReviewedResult(id=row.id, reviewed=row.reviewed)

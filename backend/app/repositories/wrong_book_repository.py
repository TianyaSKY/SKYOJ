"""错题本仓储。"""

from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.wrong_book import WrongBook


class WrongBookRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert(
        self,
        *,
        user_id: int,
        problem_id: int,
        submission_id: int,
        now: datetime,
    ) -> WrongBook:
        """写入或更新错题本：WA/TLE/RE 时调用；Accepted 时改为 accepted=True。"""
        existing = (
            self._db.query(WrongBook)
            .filter(
                WrongBook.user_id == user_id,
                WrongBook.problem_id == problem_id,
            )
            .first()
        )
        if existing is not None:
            if existing.accepted:
                # 学生之前 ac 过了，现在又 wa，说明重新出错。
                existing.accepted = False
                existing.reviewed = False
            existing.latest_wrong_at = now
            existing.submission_id = submission_id
            self._db.flush()
            return existing
        entry = WrongBook(
            user_id=user_id,
            problem_id=problem_id,
            first_wrong_at=now,
            latest_wrong_at=now,
            submission_id=submission_id,
            accepted=False,
            reviewed=False,
        )
        self._db.add(entry)
        self._db.flush()
        return entry

    def mark_accepted(self, user_id: int, problem_id: int) -> None:
        """学生 ac 后从错题本移除（标记 accepted=True）。"""
        row = (
            self._db.query(WrongBook)
            .filter(
                WrongBook.user_id == user_id,
                WrongBook.problem_id == problem_id,
            )
            .first()
        )
        if row is not None:
            row.accepted = True
            self._db.flush()

    def toggle_reviewed(self, entry_id: int) -> WrongBook:
        row = self._db.get(WrongBook, entry_id)
        if row is not None:
            row.reviewed = not row.reviewed
            self._db.flush()
        return row

    def list_for_user(
        self,
        user_id: int,
        *,
        unresolved_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WrongBook], int]:
        query = (
            self._db.query(WrongBook)
            .filter(WrongBook.user_id == user_id)
            .order_by(WrongBook.latest_wrong_at.desc())
        )
        if unresolved_only:
            query = query.filter(
                or_(WrongBook.accepted == False, WrongBook.accepted.is_(None))  # noqa: E712
            )
        total = query.count()
        rows = (
            query.offset((page - 1) * page_size).limit(page_size).all()
        )
        return rows, total

    def get_stats(self, user_id: int) -> tuple[int, int, int, int]:
        rows = (
            self._db.query(WrongBook)
            .filter(WrongBook.user_id == user_id)
            .all()
        )
        total = len(rows)
        unresolved = sum(1 for r in rows if not r.accepted)
        reviewed = sum(1 for r in rows if r.reviewed)
        accepted = sum(1 for r in rows if r.accepted)
        return total, unresolved, reviewed, accepted

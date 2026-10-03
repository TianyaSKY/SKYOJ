"""user 数据库模型、仓储与映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    and_,
    func,
    or_,
)
from sqlalchemy.orm import Session, relationship, selectinload

from app.persistence.database import Base
from app.persistence.problem import ProblemRecord


@dataclass
class UserRecord:
    """User 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    username: str
    password_hash: str
    role: str | None
    avatar: str | None


@dataclass
class WrongBookRecord:
    """WrongBook 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    user_id: int
    problem_id: int
    first_wrong_at: datetime
    latest_wrong_at: datetime
    submission_id: int | None
    accepted: bool
    reviewed: bool
    created_at: datetime
    updated_at: datetime
    problem: ProblemRecord | None


if TYPE_CHECKING:
    from app.persistence.submission import SubmissionRecord


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    # role: enum('student', 'teacher')
    role = Column(Enum("student", "teacher"), default="student")
    avatar = Column(String(255))  # 头像 URL 或文件名

    submissions = relationship("Submission", back_populates="user", lazy=True)
    datasets = relationship("Dataset", back_populates="uploader", lazy=True)
    created_exams = relationship("Exam", back_populates="creator", lazy=True)
    search_history = relationship("SearchHistory", back_populates="user", lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"


class WrongBook(Base):
    """学生错题本：每道被标记为错误的题目（WA/TLE/RE）在此留一条记录。

    设计原则：
    - 每道题每个学生最多一条（通过 unique constraint 保证）。
    - 首次错题写入；后续同一题再次错题时更新 latest_attempt_at。
    - accepted=True 时自动从错题本移除（学生 ac 后不再是"错题"）。
    - reviewed=True 时标记为已复习。
    """

    __tablename__ = "wrong_books"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "problem_id",
            name="uq_wrong_books_user_problem",
        ),
        Index("ix_wrong_books_user", "user_id"),
        Index("ix_wrong_books_problem", "problem_id"),
        Index("ix_wrong_books_accepted", "accepted"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    # 首次错题时填入；每次同类错题重犯时更新。
    first_wrong_at = Column(DateTime, nullable=False)
    latest_wrong_at = Column(DateTime, nullable=False)
    # 提交 id（方便定位到具体哪次提交出错的代码）。
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    # 是否已 AC：是则从错题本移除（学生已掌握）
    accepted = Column(Boolean, default=False, nullable=False)
    # 是否已复习
    reviewed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")
    problem = relationship("Problem")
    submission = relationship("Submission")

    def __repr__(self) -> str:
        return f"<WrongBook user={self.user_id} problem={self.problem_id} accepted={self.accepted}>"


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="search_history")

    def __repr__(self):
        return f"<SearchHistory {self.query} by User {self.user_id}>"


class UserRepository:
    """封装用户表的读写操作。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        """按用户名查询用户。"""
        return _to_user_record(
            self._db.query(User).filter_by(username=username).first()
        )

    def create(self, username: str, password_hash: str, role: str) -> UserRecord:
        """创建并持久化用户。"""
        user = User(username=username, password_hash=password_hash, role=role)
        self._db.add(user)
        self._db.flush()
        self._db.refresh(user)
        return _to_user_record(user)

    def get_by_id(self, user_id: int) -> Optional[UserRecord]:
        """按 ID 查询用户。"""
        return _to_user_record(self._db.get(User, user_id))

    def list_all(self) -> list[UserRecord]:
        """查询全部用户。"""
        return [_to_user_record(row) for row in (self._db.query(User).all())]

    def update_avatar(self, user: UserRecord, avatar: str) -> UserRecord:
        """更新用户头像路径。"""
        user = self._db.get(User, user.id)
        user.avatar = avatar
        self._db.flush()
        self._db.refresh(user)
        return _to_user_record(user)

    def list_submissions(self, user_id: int) -> list[SubmissionRecord]:
        """按创建时间和 ID 倒序查询用户提交，同秒记录也保持稳定顺序。"""
        from app.persistence.submission import Submission, _to_submission_record

        return [
            _to_submission_record(row)
            for row in (
                self._db.query(Submission)
                .options(
                    selectinload(Submission.user), selectinload(Submission.problem)
                )
                .filter_by(user_id=user_id)
                .order_by(Submission.created_at.desc(), Submission.id.desc())
                .all()
            )
        ]


class WrongBookRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, entry_id: int) -> WrongBookRecord | None:
        """查询用于访问控制的错题本快照。"""
        return _to_wrong_book_record(self._db.get(WrongBook, entry_id))

    def has_newer_judged_submission(
        self,
        user_id: int,
        problem_id: int,
        submission_id: int,
        relevant_statuses: tuple[str, ...],
    ) -> bool:
        """判断是否已有更新的学习结果，避免旧判题任务倒退错题状态。"""
        from app.persistence.submission import Submission

        current = self._db.get(Submission, submission_id)
        if current is None:
            return False
        return (
            self._db.query(Submission.id)
            .filter(
                Submission.user_id == user_id,
                Submission.problem_id == problem_id,
                Submission.status.in_(relevant_statuses),
                or_(
                    Submission.created_at > current.created_at,
                    and_(
                        Submission.created_at == current.created_at,
                        Submission.id > submission_id,
                    ),
                ),
            )
            .first()
            is not None
        )

    def upsert(
        self,
        *,
        user_id: int,
        problem_id: int,
        submission_id: int,
        now: datetime,
    ) -> WrongBookRecord:
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
            return _to_wrong_book_record(existing)
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
        return _to_wrong_book_record(entry)

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

    def toggle_reviewed(self, entry_id: int) -> WrongBookRecord:
        row = self._db.get(WrongBook, entry_id)
        if row is not None:
            row.reviewed = not row.reviewed
            self._db.flush()
        return _to_wrong_book_record(row)

    def list_for_user(
        self,
        user_id: int,
        *,
        unresolved_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WrongBookRecord], int]:
        query = (
            self._db.query(WrongBook)
            .options(selectinload(WrongBook.problem))
            .filter(WrongBook.user_id == user_id)
            .order_by(WrongBook.latest_wrong_at.desc())
        )
        if unresolved_only:
            query = query.filter(
                or_(WrongBook.accepted == False, WrongBook.accepted.is_(None))  # noqa: E712
            )
        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        return ([_to_wrong_book_record(row) for row in (rows)], total)

    def get_stats(self, user_id: int) -> tuple[int, int, int, int]:
        rows = (
            self._db.query(WrongBook)
            .options(selectinload(WrongBook.problem))
            .filter(WrongBook.user_id == user_id)
            .all()
        )
        total = len(rows)
        unresolved = sum(1 for r in rows if not r.accepted)
        reviewed = sum(1 for r in rows if r.reviewed)
        accepted = sum(1 for r in rows if r.accepted)
        return total, unresolved, reviewed, accepted


class SearchRepository:
    """封装普通搜索及搜索历史持久化。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def search_problems(self, query: str, top_k: int):

        from app.persistence.problem import Problem, _to_problem_record

        return [
            _to_problem_record(row)
            for row in (
                self._db.query(Problem)
                .filter(
                    or_(
                        Problem.title.like(f"%{query}%"),
                        Problem.content.like(f"%{query}%"),
                    )
                )
                .limit(top_k)
                .all()
            )
        ]

    def add_history(self, user_id: int, query: str) -> None:
        self._db.add(SearchHistory(user_id=user_id, query=query))
        self._db.flush()


def _to_user_record(row: User | None) -> UserRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, UserRecord):
        return row
    return UserRecord(
        id=row.id,
        username=row.username,
        password_hash=row.password_hash,
        role=row.role,
        avatar=row.avatar,
    )


def _to_wrong_book_record(row: WrongBook | None) -> WrongBookRecord | None:
    """在数据库边界复制字段和必要关系。"""
    from app.persistence.problem import _to_problem_record

    if row is None or isinstance(row, WrongBookRecord):
        return row
    return WrongBookRecord(
        id=row.id,
        user_id=row.user_id,
        problem_id=row.problem_id,
        first_wrong_at=row.first_wrong_at,
        latest_wrong_at=row.latest_wrong_at,
        submission_id=row.submission_id,
        accepted=row.accepted,
        reviewed=row.reviewed,
        created_at=row.created_at,
        updated_at=row.updated_at,
        problem=_to_problem_record(row.problem),
    )

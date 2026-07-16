"""用户数据访问。"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.submission import Submission


class UserRepository:
    """封装用户表的读写操作。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_username(self, username: str) -> Optional[User]:
        """按用户名查询用户。"""
        return self._db.query(User).filter_by(username=username).first()

    def create(self, username: str, password_hash: str, role: str) -> User:
        """创建并持久化用户。"""
        user = User(username=username, password_hash=password_hash, role=role)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """按 ID 查询用户。"""
        return self._db.get(User, user_id)

    def list_all(self) -> list[User]:
        """查询全部用户。"""
        return self._db.query(User).all()

    def update_avatar(self, user: User, avatar: str) -> User:
        """更新用户头像路径。"""
        user.avatar = avatar
        self._db.commit()
        self._db.refresh(user)
        return user

    def list_submissions(self, user_id: int) -> list[Submission]:
        """按创建时间倒序查询用户的提交记录。"""
        return (
            self._db.query(Submission)
            .filter_by(user_id=user_id)
            .order_by(Submission.created_at.desc())
            .all()
        )

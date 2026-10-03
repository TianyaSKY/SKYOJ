"""system 数据库模型、仓储与映射。"""

from __future__ import annotations

from app.persistence.database import Base
from app.persistence.unit_of_work import UnitOfWork
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Session, relationship
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.services.system import SystemStatistics
    from app.persistence.exam import Exam
    from app.persistence.problem import Problem
    from app.persistence.submission import Submission
    from app.persistence.user import User


class SysDict(Base):
    __tablename__ = "sys_dict"

    id = Column(Integer, primary_key=True)
    key = Column(String(100))
    val = Column(String(100))


class AuditLog(Base):
    """审计日志：记录写操作（POST/PUT/DELETE）和敏感读取。"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    method = Column(String(16), nullable=False)
    path = Column(String(255), nullable=False)
    status_code = Column(Integer)
    ip = Column(String(64))
    user_agent = Column(String(255))
    payload_summary = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} {self.method} {self.path} status={self.status_code}>"


class SystemRepository:
    """封装系统配置及统计查询。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self.unit_of_work = UnitOfWork(db)

    def get_config(self) -> dict[str, str]:
        return {item.key: item.val for item in self._db.query(SysDict).all()}

    def save_config(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            item = self._db.query(SysDict).filter_by(key=key).first()
            if item is None:
                self._db.add(SysDict(key=key, val=value))
            else:
                item.val = value
        self._db.flush()

    def delete_config(self, key: str) -> bool:
        item = self._db.query(SysDict).filter_by(key=key).first()
        if item is None:
            return False
        self._db.delete(item)
        self._db.flush()
        return True

    def statistics(
        self, today_start: datetime, period_start: datetime, period_end: datetime
    ) -> SystemStatistics:

        from app.services.system import SystemStatistics
        from app.persistence.exam import Exam
        from app.persistence.problem import Problem
        from app.persistence.submission import Submission
        from app.persistence.user import User
        return SystemStatistics(
            today_submissions=self._db.query(Submission)
            .filter(Submission.created_at >= today_start)
            .count(),
            total_problems=self._db.query(Problem).count(),
            total_users=self._db.query(User).count(),
            exams_in_period=self._db.query(Exam)
            .filter(Exam.start_time >= period_start, Exam.start_time <= period_end)
            .count(),
        )

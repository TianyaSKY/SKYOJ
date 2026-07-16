"""系统配置与仪表盘数据访问。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.sysdict import SysDict
from app.models.user import User


class SystemRepository:
    """封装系统配置及统计查询。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_config(self) -> dict[str, str]:
        return {item.key: item.val for item in self._db.query(SysDict).all()}

    def save_config(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            item = self._db.query(SysDict).filter_by(key=key).first()
            if item is None:
                self._db.add(SysDict(key=key, val=value))
            else:
                item.val = value
        self._db.commit()

    def delete_config(self, key: str) -> bool:
        item = self._db.query(SysDict).filter_by(key=key).first()
        if item is None:
            return False
        self._db.delete(item)
        self._db.commit()
        return True

    def statistics(self, today_start: datetime, period_start: datetime, period_end: datetime) -> dict[str, int]:
        return {
            "today_submissions": self._db.query(Submission).filter(Submission.created_at >= today_start).count(),
            "total_problems": self._db.query(Problem).count(),
            "total_users": self._db.query(User).count(),
            "exams_in_period": self._db.query(Exam).filter(Exam.start_time >= period_start, Exam.start_time <= period_end).count(),
        }

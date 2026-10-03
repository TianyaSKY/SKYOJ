"""调试运行数据访问。"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.debug_run import DebugRun
from app.repositories.submission_repository import SubmissionRepository
from app.unit_of_work import UnitOfWork
from app.utils.time import utcnow


class DebugRunRepository:
    """封装 `debug_runs` 表的增改查。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self.unit_of_work = UnitOfWork(db)

    def create(
        self,
        *,
        user_id: int,
        problem_id: int,
        exam_id: Optional[int],
        language: str,
        code: str,
    ) -> DebugRun:
        """创建一条调试记录，初始状态为 Pending。"""
        row = DebugRun(
            user_id=user_id,
            problem_id=problem_id,
            exam_id=exam_id,
            language=language,
            code_content=code,
            status="Pending",
        )
        self._db.add(row)
        self._db.flush()
        self._db.refresh(row)
        return row

    def get_by_id(self, debug_run_id: int) -> Optional[DebugRun]:
        """查询单条调试记录。"""
        return self._db.get(DebugRun, debug_run_id)

    def finish(
        self,
        debug_run_id: int,
        *,
        status: str,
        case_name: Optional[str] = None,
        input_data: Optional[str] = None,
        expected_output: Optional[str] = None,
        actual_output: Optional[str] = None,
        error_output: Optional[str] = None,
        time_used_ms: Optional[int] = None,
        memory_used_kb: Optional[int] = None,
    ) -> None:
        """写入最终结果。"""
        values: dict[str, object] = {
            "status": status,
            "finished_at": utcnow(),
        }
        if case_name is not None:
            values["case_name"] = case_name
        if input_data is not None:
            values["input"] = input_data
        if expected_output is not None:
            values["expected_output"] = expected_output
        if actual_output is not None:
            values["actual_output"] = actual_output
        if error_output is not None:
            values["error_output"] = error_output
        if time_used_ms is not None:
            values["time_used_ms"] = time_used_ms
        if memory_used_kb is not None:
            values["memory_used_kb"] = memory_used_kb
        self._db.query(DebugRun).filter(DebugRun.id == debug_run_id).update(values)
        self._db.flush()

    def get_problem(self, problem_id: int):
        return SubmissionRepository(self._db).get_problem(problem_id)

    def get_active_exam(self, exam_id: int, now: datetime):
        return SubmissionRepository(self._db).get_active_exam(exam_id, now)


__all__ = ["DebugRunRepository"]

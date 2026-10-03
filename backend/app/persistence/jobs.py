"""jobs 数据库模型、仓储与映射。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    and_,
    func,
    or_,
    update,
)
from sqlalchemy.orm import Session, relationship

from app.core.time import utcnow
from app.persistence.database import Base


@dataclass
class AiDraftRecord:
    """AiDraft 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    user_id: int
    task_type: str
    status: str
    title: str
    problem_id: int | None
    request_payload: str | None
    result_payload: str | None
    error_message: str | None
    created_at: datetime | None
    updated_at: datetime | None
    consumed_at: datetime | None


@dataclass
class AsyncJobRecord:
    """AsyncJob 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    task_name: str
    queue: str
    payload: str
    status: str
    dedupe_key: str | None
    attempts: int
    max_attempts: int
    lease_until: datetime | None
    available_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


JOB_PENDING = "pending"
JOB_RUNNING = "running"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"


class AsyncJob(Base):
    """保存业务异步任务状态；RabbitMQ 消息只携带该任务的 ID。"""

    __tablename__ = "async_jobs"

    id = Column(Integer, primary_key=True)
    task_name = Column(String(128), nullable=False)
    queue = Column(String(32), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    dedupe_key = Column(String(255), nullable=True, unique=True)

    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    lease_until = Column(DateTime, nullable=True, index=True)
    available_at = Column(DateTime, nullable=False, default=utcnow, index=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    __table_args__ = (
        Index("ix_async_jobs_status_available", "status", "available_at"),
    )

    def __repr__(self) -> str:
        return f"<AsyncJob {self.id} {self.task_name} {self.status}>"


class AiDraft(Base):
    """存储 AI 出题 / 测例生成等异步任务及其结果。"""

    __tablename__ = "ai_drafts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # problem_generation | test_script_generation | test_data_execution
    task_type = Column(String(64), nullable=False, index=True)
    # pending | running | success | failed
    status = Column(String(32), nullable=False, default="pending", index=True)

    title = Column(String(255), nullable=False, default="")
    # 关联题目（测例相关任务）
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)

    request_payload = Column(Text, nullable=True)
    result_payload = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # 出题草稿被应用到正式题目的时间
    consumed_at = Column(DateTime, nullable=True)

    user = relationship("User", lazy=True)
    problem = relationship("Problem", lazy=True)

    def __repr__(self) -> str:
        return f"<AiDraft {self.id} {self.task_type} {self.status}>"


class AsyncJobRepository:
    """封装 async_jobs 表的读写。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        task_name: str,
        queue: str,
        payload: dict[str, Any],
        dedupe_key: Optional[str],
        max_attempts: int,
        available_at: datetime,
    ) -> AsyncJobRecord:
        """创建任务记录。"""

        job = AsyncJob(
            task_name=task_name,
            queue=queue,
            payload=json.dumps(payload, ensure_ascii=False),
            status=JOB_PENDING,
            dedupe_key=dedupe_key,
            max_attempts=max(1, max_attempts),
            available_at=available_at,
        )
        self._db.add(job)
        self._db.flush()
        self._db.refresh(job)
        return _to_async_job_record(job)

    def get_by_id(self, job_id: int) -> Optional[AsyncJobRecord]:
        """按主键查询任务。"""
        return _to_async_job_record(self._db.get(AsyncJob, job_id))

    def get_by_dedupe_key(self, dedupe_key: str) -> Optional[AsyncJobRecord]:
        """按幂等键查询已有任务。"""
        return _to_async_job_record(
            self._db.query(AsyncJob).filter(AsyncJob.dedupe_key == dedupe_key).first()
        )

    def delete(self, job: AsyncJobRecord) -> None:
        """删除任务记录（用于投递失败时撤销未发布任务）。"""
        self._db.delete(self._db.get(AsyncJob, job.id))
        self._db.flush()

    def claim(
        self, job_id: int, *, now: datetime, lease_until: datetime
    ) -> Optional[AsyncJobRecord]:
        """以单进程任务语义领取任务；重复投递时只允许一个执行者继续。"""

        job = self._db.get(AsyncJob, job_id)
        if job is None:
            return None
        if job.status in {JOB_SUCCEEDED, JOB_FAILED}:
            return None
        if job.available_at > now:
            return None
        if job.status == JOB_RUNNING and job.lease_until and job.lease_until > now:
            return None
        if job.attempts >= job.max_attempts:
            job.status = JOB_FAILED
            job.finished_at = now
            job.lease_until = None
            job.updated_at = now
            self._db.flush()
            return None

        claim_statement = (
            update(AsyncJob)
            .where(
                AsyncJob.id == job_id,
                AsyncJob.available_at <= now,
                AsyncJob.attempts < AsyncJob.max_attempts,
                or_(
                    AsyncJob.status == JOB_PENDING,
                    and_(
                        AsyncJob.status == JOB_RUNNING,
                        AsyncJob.lease_until.is_not(None),
                        AsyncJob.lease_until <= now,
                    ),
                ),
            )
            .values(
                status=JOB_RUNNING,
                attempts=AsyncJob.attempts + 1,
                started_at=func.coalesce(AsyncJob.started_at, now),
                lease_until=lease_until,
                updated_at=now,
            )
        )
        result = self._db.execute(claim_statement)
        if result.rowcount != 1:
            return None
        self._db.flush()
        return _to_async_job_record(self.get_by_id(job_id))

    def mark_succeeded(self, job_id: int, *, now: datetime) -> Optional[AsyncJobRecord]:
        """标记任务成功。"""

        job = self._db.get(AsyncJob, job_id)
        if job is None:
            return None
        job.status = JOB_SUCCEEDED
        job.finished_at = now
        job.lease_until = None
        job.last_error = None
        job.updated_at = now
        self._db.flush()
        self._db.refresh(job)
        return _to_async_job_record(job)

    def mark_failed(
        self,
        job_id: int,
        *,
        error_message: str,
        now: datetime,
        retry_at: Optional[datetime],
    ) -> Optional[AsyncJobRecord]:
        """记录失败；仍有次数时将任务重新置为待处理。"""

        job = self._db.get(AsyncJob, job_id)
        if job is None:
            return None

        job.last_error = error_message[:4000]
        job.lease_until = None
        job.updated_at = now
        if retry_at is not None and job.attempts < job.max_attempts:
            job.status = JOB_PENDING
            job.available_at = retry_at
        else:
            job.status = JOB_FAILED
            job.finished_at = now
        self._db.flush()
        self._db.refresh(job)
        return _to_async_job_record(job)

    def recover_expired(self, *, now: datetime, limit: int) -> list[AsyncJobRecord]:
        """恢复失联任务：RUNNING 租约过期置回待处理，PENDING 且已到
        available_at 的任务重新投递（消息可能发布时被丢弃或提前到达被
        claim 拒收）。重复投递由 claim 的原子领取吸收。"""

        jobs = (
            self._db.query(AsyncJob)
            .filter(
                or_(
                    and_(
                        AsyncJob.status == JOB_RUNNING,
                        AsyncJob.lease_until.is_not(None),
                        AsyncJob.lease_until <= now,
                    ),
                    and_(
                        AsyncJob.status == JOB_PENDING,
                        AsyncJob.available_at <= now,
                    ),
                )
            )
            .order_by(AsyncJob.id.asc())
            .limit(max(1, min(limit, 100)))
            .all()
        )
        recovered = []
        for job in jobs:
            if job.status == JOB_RUNNING:
                if job.attempts >= job.max_attempts:
                    job.status = JOB_FAILED
                    job.finished_at = now
                    job.lease_until = None
                else:
                    job.status = JOB_PENDING
                    job.available_at = now
                    job.lease_until = None
                    recovered.append(job)
            else:
                recovered.append(job)
            job.updated_at = now
        self._db.flush()
        return [_to_async_job_record(row) for row in (recovered)]

    @staticmethod
    def parse_payload(raw: str) -> dict[str, Any]:
        """解析任务参数。"""
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("异步任务参数不是有效 JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("异步任务参数必须是 JSON 对象")
        return payload


class AiDraftRepository:
    """ai_drafts 表读写。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: int,
        task_type: str,
        title: str,
        request_payload: dict[str, Any],
        problem_id: Optional[int] = None,
        status: str = "pending",
    ) -> AiDraftRecord:
        """创建草稿记录。"""
        draft = AiDraft(
            user_id=user_id,
            task_type=task_type,
            status=status,
            title=title,
            problem_id=problem_id,
            request_payload=json.dumps(request_payload, ensure_ascii=False),
        )
        self._db.add(draft)
        self._db.flush()
        self._db.refresh(draft)
        return _to_ai_draft_record(draft)

    def get_by_id(self, draft_id: int) -> Optional[AiDraftRecord]:
        """按主键查询。"""
        return _to_ai_draft_record(self._db.get(AiDraft, draft_id))

    def list_by_user(
        self,
        user_id: int,
        *,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[AiDraftRecord]:
        """按用户列出草稿，新的在前。"""
        query = self._db.query(AiDraft).filter(AiDraft.user_id == user_id)
        if status:
            query = query.filter(AiDraft.status == status)
        if task_type:
            query = query.filter(AiDraft.task_type == task_type)
        return [
            _to_ai_draft_record(row)
            for row in (
                query.order_by(AiDraft.id.desc()).limit(max(1, min(limit, 200))).all()
            )
        ]

    def mark_running(self, draft_id: int) -> Optional[AiDraftRecord]:
        """将任务标记为运行中。"""
        draft = self._db.get(AiDraft, draft_id)
        if draft is None:
            return None
        draft.status = "running"
        draft.updated_at = datetime.utcnow()
        self._db.flush()
        self._db.refresh(draft)
        return _to_ai_draft_record(draft)

    def mark_success(
        self,
        draft_id: int,
        *,
        result_payload: dict[str, Any],
        title: Optional[str] = None,
    ) -> Optional[AiDraftRecord]:
        """将任务标记为成功并写入结果。"""
        draft = self._db.get(AiDraft, draft_id)
        if draft is None:
            return None
        draft.status = "success"
        draft.result_payload = json.dumps(result_payload, ensure_ascii=False)
        draft.error_message = None
        if title:
            draft.title = title
        draft.updated_at = datetime.utcnow()
        self._db.flush()
        self._db.refresh(draft)
        return _to_ai_draft_record(draft)

    def mark_failed(self, draft_id: int, error_message: str) -> Optional[AiDraftRecord]:
        """将任务标记为失败。"""
        draft = self._db.get(AiDraft, draft_id)
        if draft is None:
            return None
        draft.status = "failed"
        draft.error_message = error_message[:2000]
        draft.updated_at = datetime.utcnow()
        self._db.flush()
        self._db.refresh(draft)
        return _to_ai_draft_record(draft)

    def mark_consumed(self, draft_id: int) -> Optional[AiDraftRecord]:
        """标记草稿已被应用到正式题目。"""
        draft = self._db.get(AiDraft, draft_id)
        if draft is None:
            return None
        draft.consumed_at = datetime.utcnow()
        draft.updated_at = datetime.utcnow()
        self._db.flush()
        self._db.refresh(draft)
        return _to_ai_draft_record(draft)

    def delete(self, draft: AiDraftRecord) -> None:
        """删除草稿。"""
        self._db.delete(self._db.get(AiDraft, draft.id))
        self._db.flush()

    def count_stats(self, user_id: int) -> dict[str, int]:
        """统计用户草稿各状态数量。"""
        rows = (
            self._db.query(AiDraft.status, func.count(AiDraft.id))
            .filter(AiDraft.user_id == user_id)
            .group_by(AiDraft.status)
            .all()
        )
        by_status = {status: count for status, count in rows}
        total = sum(by_status.values())
        unconsumed_success = (
            self._db.query(func.count(AiDraft.id))
            .filter(
                AiDraft.user_id == user_id,
                AiDraft.status == "success",
                AiDraft.consumed_at.is_(None),
            )
            .scalar()
            or 0
        )
        return {
            "total": total,
            "pending": by_status.get("pending", 0),
            "running": by_status.get("running", 0),
            "success": by_status.get("success", 0),
            "failed": by_status.get("failed", 0),
            "unconsumed_success": int(unconsumed_success),
        }

    @staticmethod
    def parse_json_field(raw: Optional[str]) -> dict[str, Any]:
        """将 Text 字段解析为 dict。"""
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"value": data}
        except json.JSONDecodeError:
            return {"raw": raw}


def _to_async_job_record(row: AsyncJob | None) -> AsyncJobRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, AsyncJobRecord):
        return row
    return AsyncJobRecord(
        id=row.id,
        task_name=row.task_name,
        queue=row.queue,
        payload=row.payload,
        status=row.status,
        dedupe_key=row.dedupe_key,
        attempts=row.attempts,
        max_attempts=row.max_attempts,
        lease_until=row.lease_until,
        available_at=row.available_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_ai_draft_record(row: AiDraft | None) -> AiDraftRecord | None:
    """在数据库边界复制字段和必要关系。"""

    if row is None or isinstance(row, AiDraftRecord):
        return row
    return AiDraftRecord(
        id=row.id,
        user_id=row.user_id,
        task_type=row.task_type,
        status=row.status,
        title=row.title,
        problem_id=row.problem_id,
        request_payload=row.request_payload,
        result_payload=row.result_payload,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
        consumed_at=row.consumed_at,
    )

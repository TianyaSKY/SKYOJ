"""jobs 数据库模型、仓储与映射。"""

from __future__ import annotations

import json
from app.core.time import utcnow
from app.persistence.database import Base
from app.persistence.unit_of_work import UnitOfWork
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, and_, func, or_, update
from sqlalchemy.orm import Session, relationship
from typing import Any, Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from app.services.async_job import JOB_FAILED, JOB_PENDING, JOB_RUNNING, JOB_SUCCEEDED
    from app.services.ai_draft import AiDraftDetail, AiDraftSummary
    from app.services.async_job import AsyncJobResult


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
        self.unit_of_work = UnitOfWork(db)

    def create(
        self,
        *,
        task_name: str,
        queue: str,
        payload: dict[str, Any],
        dedupe_key: Optional[str],
        max_attempts: int,
        available_at: datetime,
    ) -> AsyncJob:
        """创建任务记录。"""

        from app.services.async_job import JOB_PENDING
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
        return job

    def get_by_id(self, job_id: int) -> Optional[AsyncJob]:
        """按主键查询任务。"""
        return self._db.get(AsyncJob, job_id)

    def get_by_dedupe_key(self, dedupe_key: str) -> Optional[AsyncJob]:
        """按幂等键查询已有任务。"""
        return (
            self._db.query(AsyncJob).filter(AsyncJob.dedupe_key == dedupe_key).first()
        )

    def delete(self, job: AsyncJob) -> None:
        """删除任务记录（用于投递失败时撤销未发布任务）。"""
        self._db.delete(job)
        self._db.flush()

    def claim(
        self, job_id: int, *, now: datetime, lease_until: datetime
    ) -> Optional[AsyncJob]:
        """以单进程任务语义领取任务；重复投递时只允许一个执行者继续。"""

        from app.services.async_job import JOB_FAILED, JOB_PENDING, JOB_RUNNING, JOB_SUCCEEDED
        job = self.get_by_id(job_id)
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
        return self.get_by_id(job_id)

    def mark_succeeded(self, job_id: int, *, now: datetime) -> Optional[AsyncJob]:
        """标记任务成功。"""

        from app.services.async_job import JOB_SUCCEEDED
        job = self.get_by_id(job_id)
        if job is None:
            return None
        job.status = JOB_SUCCEEDED
        job.finished_at = now
        job.lease_until = None
        job.last_error = None
        job.updated_at = now
        self._db.flush()
        self._db.refresh(job)
        return job

    def mark_failed(
        self,
        job_id: int,
        *,
        error_message: str,
        now: datetime,
        retry_at: Optional[datetime],
    ) -> Optional[AsyncJob]:
        """记录失败；仍有次数时将任务重新置为待处理。"""

        from app.services.async_job import JOB_FAILED, JOB_PENDING
        job = self.get_by_id(job_id)
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
        return job

    def recover_expired(self, *, now: datetime, limit: int) -> list[AsyncJob]:
        """恢复失联任务：RUNNING 租约过期置回待处理，PENDING 且已到
        available_at 的任务重新投递（消息可能发布时被丢弃或提前到达被
        claim 拒收）。重复投递由 claim 的原子领取吸收。"""

        from app.services.async_job import JOB_FAILED, JOB_PENDING, JOB_RUNNING
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
        return recovered

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
        self.unit_of_work = UnitOfWork(db)

    def create(
        self,
        *,
        user_id: int,
        task_type: str,
        title: str,
        request_payload: dict[str, Any],
        problem_id: Optional[int] = None,
        status: str = "pending",
    ) -> AiDraft:
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
        return draft

    def get_by_id(self, draft_id: int) -> Optional[AiDraft]:
        """按主键查询。"""
        return self._db.get(AiDraft, draft_id)

    def list_by_user(
        self,
        user_id: int,
        *,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[AiDraft]:
        """按用户列出草稿，新的在前。"""
        query = self._db.query(AiDraft).filter(AiDraft.user_id == user_id)
        if status:
            query = query.filter(AiDraft.status == status)
        if task_type:
            query = query.filter(AiDraft.task_type == task_type)
        return query.order_by(AiDraft.id.desc()).limit(max(1, min(limit, 200))).all()

    def mark_running(self, draft_id: int) -> Optional[AiDraft]:
        """将任务标记为运行中。"""
        draft = self.get_by_id(draft_id)
        if draft is None:
            return None
        draft.status = "running"
        draft.updated_at = datetime.utcnow()
        self._db.flush()
        self._db.refresh(draft)
        return draft

    def mark_success(
        self,
        draft_id: int,
        *,
        result_payload: dict[str, Any],
        title: Optional[str] = None,
    ) -> Optional[AiDraft]:
        """将任务标记为成功并写入结果。"""
        draft = self.get_by_id(draft_id)
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
        return draft

    def mark_failed(self, draft_id: int, error_message: str) -> Optional[AiDraft]:
        """将任务标记为失败。"""
        draft = self.get_by_id(draft_id)
        if draft is None:
            return None
        draft.status = "failed"
        draft.error_message = error_message[:2000]
        draft.updated_at = datetime.utcnow()
        self._db.flush()
        self._db.refresh(draft)
        return draft

    def mark_consumed(self, draft_id: int) -> Optional[AiDraft]:
        """标记草稿已被应用到正式题目。"""
        draft = self.get_by_id(draft_id)
        if draft is None:
            return None
        draft.consumed_at = datetime.utcnow()
        draft.updated_at = datetime.utcnow()
        self._db.flush()
        self._db.refresh(draft)
        return draft

    def delete(self, draft: AiDraft) -> None:
        """删除草稿。"""
        self._db.delete(draft)
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


def from_ai_draft_orm(draft, *, detail: bool = False) -> AiDraftSummary | AiDraftDetail:
    """AI 草稿 ORM → 列表项或详情。"""

    from app.services.ai_draft import AiDraftDetail, AiDraftSummary
    if detail:
        return AiDraftDetail(
            id=draft.id,
            task_type=draft.task_type,
            status=draft.status,
            title=draft.title or "",
            problem_id=draft.problem_id,
            request_payload=AiDraftRepository.parse_json_field(draft.request_payload),
            result_payload=AiDraftRepository.parse_json_field(draft.result_payload),
            error_message=draft.error_message,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            consumed_at=draft.consumed_at,
        )
    return AiDraftSummary(
        id=draft.id,
        task_type=draft.task_type,
        status=draft.status,
        title=draft.title or "",
        problem_id=draft.problem_id,
        error_message=draft.error_message,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        consumed_at=draft.consumed_at,
    )


def from_async_job_orm(job) -> AsyncJobResult:
    """异步任务 ORM → 对外快照。"""

    from app.services.async_job import AsyncJobResult
    return AsyncJobResult(
        id=job.id,
        task_name=job.task_name,
        queue=job.queue,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        lease_until=job.lease_until,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )

"""异步任务与 Outbox 数据访问。"""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, func, or_, update
from sqlalchemy.orm import Session

from app.domain.async_job import (
    JOB_FAILED,
    JOB_PENDING,
    JOB_RUNNING,
    JOB_SUCCEEDED,
    OUTBOX_PENDING,
    OUTBOX_PUBLISHED,
)
from app.models.async_job import AsyncJob, AsyncJobOutbox
from app.utils.time import utcnow


class AsyncJobRepository:
    """封装 async_jobs 与 async_job_outbox 表的读写。"""

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
    ) -> AsyncJob:
        """在同一事务内创建任务和 Outbox 记录。"""
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
        self._db.add(
            AsyncJobOutbox(
                job_id=job.id,
                status=OUTBOX_PENDING,
                available_at=available_at,
            )
        )
        self._db.commit()
        self._db.refresh(job)
        return job

    def get_by_id(self, job_id: int) -> Optional[AsyncJob]:
        """按主键查询任务。"""
        return self._db.get(AsyncJob, job_id)

    def rollback(self) -> None:
        """回滚当前事务。"""
        self._db.rollback()

    def get_by_dedupe_key(self, dedupe_key: str) -> Optional[AsyncJob]:
        """按幂等键查询已有任务。"""
        return (
            self._db.query(AsyncJob)
            .filter(AsyncJob.dedupe_key == dedupe_key)
            .first()
        )

    def list_pending_outbox(
        self, *, now: datetime, limit: int
    ) -> list[AsyncJobOutbox]:
        """列出到期且对应任务仍待执行的 Outbox 记录。"""
        return (
            self._db.query(AsyncJobOutbox)
            .join(AsyncJob)
            .filter(
                AsyncJobOutbox.status == OUTBOX_PENDING,
                AsyncJobOutbox.available_at <= now,
                AsyncJob.status == JOB_PENDING,
                AsyncJob.available_at <= now,
            )
            .order_by(AsyncJobOutbox.id.asc())
            .limit(max(1, min(limit, 100)))
            .all()
        )

    def mark_outbox_published(
        self, outbox_id: int, *, published_at: datetime
    ) -> Optional[AsyncJobOutbox]:
        """标记 Outbox 消息已经提交给 RabbitMQ。"""
        outbox = self._db.get(AsyncJobOutbox, outbox_id)
        if outbox is None:
            return None
        outbox.status = OUTBOX_PUBLISHED
        outbox.published_at = published_at
        outbox.last_error = None
        outbox.updated_at = published_at
        self._db.commit()
        self._db.refresh(outbox)
        return outbox

    def mark_outbox_pending(
        self,
        outbox_id: int,
        *,
        error_message: str,
        available_at: datetime,
    ) -> Optional[AsyncJobOutbox]:
        """发布失败时保留 Outbox，并等待下一轮重试。"""
        outbox = self._db.get(AsyncJobOutbox, outbox_id)
        if outbox is None:
            return None
        outbox.status = OUTBOX_PENDING
        outbox.attempts += 1
        outbox.available_at = available_at
        outbox.last_error = error_message[:2000]
        outbox.updated_at = utcnow()
        self._db.commit()
        self._db.refresh(outbox)
        return outbox

    def claim(self, job_id: int, *, now: datetime, lease_until: datetime) -> Optional[AsyncJob]:
        """以单进程任务语义领取任务；重复投递时只允许一个执行者继续。"""
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
            self._db.commit()
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
            self._db.rollback()
            return None
        self._db.commit()
        return self.get_by_id(job_id)

    def mark_succeeded(self, job_id: int, *, now: datetime) -> Optional[AsyncJob]:
        """标记任务成功。"""
        job = self.get_by_id(job_id)
        if job is None:
            return None
        job.status = JOB_SUCCEEDED
        job.finished_at = now
        job.lease_until = None
        job.last_error = None
        job.updated_at = now
        if job.outbox is not None and job.outbox.status != OUTBOX_PUBLISHED:
            job.outbox.status = OUTBOX_PUBLISHED
            job.outbox.published_at = now
            job.outbox.updated_at = now
        self._db.commit()
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
        """记录失败；仍有次数时将任务和 Outbox 一起重新置为待处理。"""
        job = self.get_by_id(job_id)
        if job is None:
            return None

        job.last_error = error_message[:4000]
        job.lease_until = None
        job.updated_at = now
        if retry_at is not None and job.attempts < job.max_attempts:
            job.status = JOB_PENDING
            job.available_at = retry_at
            if job.outbox is not None:
                job.outbox.status = OUTBOX_PENDING
                job.outbox.available_at = retry_at
                job.outbox.last_error = error_message[:2000]
                job.outbox.updated_at = now
        else:
            job.status = JOB_FAILED
            job.finished_at = now
        self._db.commit()
        self._db.refresh(job)
        return job

    def renew_lease(
        self, job_id: int, *, now: datetime, lease_until: datetime
    ) -> Optional[AsyncJob]:
        """主动延长任务租约。"""
        job = self.get_by_id(job_id)
        if job is None or job.status != JOB_RUNNING:
            return None
        job.lease_until = lease_until
        job.updated_at = now
        self._db.commit()
        self._db.refresh(job)
        return job

    def recover_expired(self, *, now: datetime, limit: int) -> int:
        """将过期运行中任务重新放回 Outbox；超过次数的任务标记失败。"""
        jobs = (
            self._db.query(AsyncJob)
            .filter(
                AsyncJob.status == JOB_RUNNING,
                AsyncJob.lease_until.is_not(None),
                AsyncJob.lease_until <= now,
            )
            .order_by(AsyncJob.id.asc())
            .limit(max(1, min(limit, 100)))
            .all()
        )
        recovered = 0
        for job in jobs:
            if job.attempts >= job.max_attempts:
                job.status = JOB_FAILED
                job.finished_at = now
                job.lease_until = None
            else:
                job.status = JOB_PENDING
                job.available_at = now
                job.lease_until = None
                if job.outbox is not None:
                    job.outbox.status = OUTBOX_PENDING
                    job.outbox.available_at = now
                    job.outbox.last_error = "任务租约已过期，等待重新投递"
                    job.outbox.updated_at = now
                recovered += 1
            job.updated_at = now
        self._db.commit()
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


__all__ = ["AsyncJobRepository"]

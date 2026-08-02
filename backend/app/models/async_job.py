"""异步任务和 Outbox 事件模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time import utcnow


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

    outbox = relationship(
        "AsyncJobOutbox",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_async_jobs_status_available", "status", "available_at"),
    )

    def __repr__(self) -> str:
        return f"<AsyncJob {self.id} {self.task_name} {self.status}>"


class AsyncJobOutbox(Base):
    """待发布到 RabbitMQ 的 Outbox 记录。"""

    __tablename__ = "async_job_outbox"

    id = Column(Integer, primary_key=True)
    job_id = Column(
        Integer,
        ForeignKey("async_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(String(32), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    published_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    job = relationship("AsyncJob", back_populates="outbox")

    def __repr__(self) -> str:
        return f"<AsyncJobOutbox {self.id} job={self.job_id} {self.status}>"


__all__ = ["AsyncJob", "AsyncJobOutbox"]

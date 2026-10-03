"""async_job 业务参数、结果与服务。"""

from __future__ import annotations

from app.core.json import JsonValue
from app.core.time import utcnow
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy.exc import IntegrityError
from typing import Optional


JOB_PENDING = "pending"
JOB_RUNNING = "running"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"

DEFAULT_MAX_ATTEMPTS = 3
# 键为消息任务名字符串，与 app.messaging.task_names 保持一致
LEASE_SECONDS = {
    "skyoj.tasks.judge_submission": 30 * 60,
    "skyoj.tasks.debug_submission": 5 * 60,
    "skyoj.tasks.execute_test_data": 20 * 60,
    "skyoj.tasks.generate_problem": 10 * 60,
    "skyoj.tasks.generate_test_script": 10 * 60,
    "skyoj.tasks.finalize_dataset": 30 * 60,
    "skyoj.tasks.scan_plagiarism": 30 * 60,
}


@dataclass(frozen=True)
class CreateAsyncJobParams:
    """创建异步任务所需参数。"""

    task_name: str
    queue: str
    payload: dict[str, JsonValue]
    dedupe_key: Optional[str] = None
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    available_at: Optional[datetime] = None


@dataclass(frozen=True)
class AsyncJobResult:
    """对外返回的任务状态快照。"""

    id: int
    task_name: str
    queue: str
    status: str
    attempts: int
    max_attempts: int
    lease_until: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


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


from app.messaging.queues import AI_QUEUE, FILE_QUEUE, JUDGE_QUEUE
from app.messaging.task_names import (
    DEBUG_SUBMISSION_TASK,
    EXECUTE_TEST_DATA_TASK,
    FINALIZE_DATASET_TASK,
    GENERATE_PROBLEM_TASK,
    GENERATE_TEST_SCRIPT_TASK,
    JUDGE_SUBMISSION_TASK,
)
from app.persistence.jobs import AsyncJobRepository, to_async_job_result


class AsyncJobService:
    """编排数据库任务状态与 RabbitMQ 发布。"""

    def __init__(self, repository: AsyncJobRepository) -> None:
        self._repository = repository

    def enqueue(self, params: CreateAsyncJobParams) -> AsyncJobResult:
        """创建任务并直接投递给 RabbitMQ；重复幂等键直接返回原任务。"""
        if params.dedupe_key:
            existing = self._repository.get_by_dedupe_key(params.dedupe_key)
            if existing is not None:
                return to_async_job_result(existing)

        available_at = params.available_at or utcnow()
        try:
            job = self._repository.create(
                task_name=params.task_name,
                queue=params.queue,
                payload=params.payload,
                dedupe_key=params.dedupe_key,
                max_attempts=params.max_attempts,
                available_at=available_at,
            )
            self._repository.unit_of_work.commit()
        except IntegrityError:
            self._repository.unit_of_work.rollback()
            if not params.dedupe_key:
                raise
            existing = self._repository.get_by_dedupe_key(params.dedupe_key)
            if existing is None:
                raise
            return to_async_job_result(existing)
        logger.info(
            "已创建异步任务 job_id={} task={} queue={}",
            job.id,
            job.task_name,
            job.queue,
        )
        try:
            self._publish(job)
        except Exception as exc:
            # 投递失败即撤销任务记录，客户端可重试（dedupe 键不复用僵尸任务）
            self._repository.delete(job)
            self._repository.unit_of_work.commit()
            logger.exception("发布异步任务失败 job_id={} queue={}", job.id, job.queue)
            raise
        return to_async_job_result(job)

    def _publish(self, job, *, countdown: int | None = None) -> None:
        """向 Celery 投递任务消息；消息体只包含任务 ID。"""
        from app.messaging.celery_app import celery_app

        kwargs = {"task_id": f"async-job-{job.id}-{job.attempts}"}
        if countdown is not None:
            kwargs["countdown"] = countdown
        celery_app.send_task(
            job.task_name,
            args=[job.id],
            queue=job.queue,
            **kwargs,
        )
        logger.info("异步任务已发布 job_id={} queue={}", job.id, job.queue)

    def enqueue_judge_submission(self, submission_id: int) -> AsyncJobResult:
        """创建判题任务。"""
        return self.enqueue(
            CreateAsyncJobParams(
                task_name=JUDGE_SUBMISSION_TASK,
                queue=JUDGE_QUEUE,
                payload={"submission_id": submission_id},
                dedupe_key=f"judge-submission:{submission_id}",
                max_attempts=3,
            )
        )

    def enqueue_debug_submission(self, debug_run_id: int) -> AsyncJobResult:
        """创建 ACM 调试运行任务。"""
        return self.enqueue(
            CreateAsyncJobParams(
                task_name=DEBUG_SUBMISSION_TASK,
                queue=JUDGE_QUEUE,
                payload={"debug_run_id": debug_run_id},
                dedupe_key=f"debug-submission:{debug_run_id}",
                max_attempts=2,
            )
        )

    def enqueue_ai_draft(self, draft_id: int, task_name: str) -> AsyncJobResult:
        """为 AI 草稿创建出题或脚本任务。"""
        if task_name not in {GENERATE_PROBLEM_TASK, GENERATE_TEST_SCRIPT_TASK}:
            raise ValueError(f"不支持的 AI 任务类型: {task_name}")
        return self.enqueue(
            CreateAsyncJobParams(
                task_name=task_name,
                queue=AI_QUEUE,
                payload={"draft_id": draft_id},
                dedupe_key=f"ai-draft:{draft_id}",
                max_attempts=3,
            )
        )

    def enqueue_test_data_execution(self, draft_id: int) -> AsyncJobResult:
        """为测试数据执行创建 Judge 任务。"""
        return self.enqueue(
            CreateAsyncJobParams(
                task_name=EXECUTE_TEST_DATA_TASK,
                queue=JUDGE_QUEUE,
                payload={"draft_id": draft_id},
                dedupe_key=f"test-data-execution:{draft_id}",
                max_attempts=3,
            )
        )

    def enqueue_finalize_dataset(self, dataset_id: int) -> AsyncJobResult:
        """为数据集文件落盘创建 File 任务。"""
        return self.enqueue(
            CreateAsyncJobParams(
                task_name=FINALIZE_DATASET_TASK,
                queue=FILE_QUEUE,
                payload={"dataset_id": dataset_id},
                dedupe_key=f"finalize-dataset:{dataset_id}",
                max_attempts=3,
            )
        )

    def start_job(self, job_id: int, *, lease_seconds: int) -> AsyncJobResult | None:
        """领取任务并写入租约；重复消息返回 None。"""
        now = utcnow()
        job = self._repository.claim(
            job_id,
            now=now,
            lease_until=now + timedelta(seconds=max(1, lease_seconds)),
        )
        self._repository.unit_of_work.commit()
        return to_async_job_result(job) if job is not None else None

    def complete_job(self, job_id: int) -> AsyncJobResult | None:
        """标记任务成功。"""
        job = self._repository.mark_succeeded(job_id, now=utcnow())
        self._repository.unit_of_work.commit()
        return to_async_job_result(job) if job is not None else None

    def fail_job(
        self,
        job_id: int,
        error_message: str,
        *,
        retry: bool = True,
    ) -> AsyncJobResult | None:
        """标记任务失败，并按剩余次数重新投递。"""
        now = utcnow()
        job = self._repository.get_by_id(job_id)
        if job is None:
            return None
        retry_at = None
        if retry and job.attempts < job.max_attempts:
            retry_at = now + timedelta(seconds=min(60, 2 ** max(0, job.attempts - 1)))
        failed = self._repository.mark_failed(
            job_id,
            error_message=error_message,
            now=now,
            retry_at=retry_at,
        )
        self._repository.unit_of_work.commit()
        if failed is not None:
            logger.warning(
                "异步任务失败 job_id={} retry={} status={} error={}",
                job_id,
                retry_at is not None,
                failed.status,
                error_message,
            )
            if retry_at is not None:
                delay = max(0, int((retry_at - now).total_seconds()))
                try:
                    self._publish(failed, countdown=delay)
                except Exception as exc:
                    logger.exception(
                        "重新投递失败任务 job_id={} queue={}",
                        job_id,
                        failed.queue,
                    )
        return to_async_job_result(failed) if failed is not None else None

    def recover_expired_jobs(self, *, limit: int = 100) -> int:
        """恢复过期租约任务并重新投递。"""
        jobs = self._repository.recover_expired(now=utcnow(), limit=limit)
        self._repository.unit_of_work.commit()
        for job in jobs:
            try:
                self._publish(job)
            except Exception as exc:
                logger.exception("重新投递过期任务失败 job_id={}", job.id)
        if jobs:
            logger.warning("已恢复过期异步任务数量={}", len(jobs))
        return len(jobs)

    @staticmethod
    def lease_seconds(task_name: str) -> int:
        """获取任务类型对应的默认租约。"""
        return LEASE_SECONDS.get(task_name, 10 * 60)

    @staticmethod
    def parse_payload(raw: str) -> dict[str, JsonValue]:
        """解析任务 JSON 参数。"""
        return AsyncJobRepository.parse_payload(raw)

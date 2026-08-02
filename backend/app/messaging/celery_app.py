"""SKYOJ Celery 应用配置。"""

from celery import Celery
from kombu import Queue

from app.config import CELERY_BROKER_URL
from app.messaging.queues import AI_QUEUE, FILE_QUEUE, JUDGE_QUEUE
from app.messaging.task_names import (
    EXECUTE_TEST_DATA_TASK,
    FINALIZE_DATASET_TASK,
    GENERATE_PROBLEM_TASK,
    GENERATE_TEST_SCRIPT_TASK,
    JUDGE_SUBMISSION_TASK,
)


celery_app = Celery("skyoj", broker=CELERY_BROKER_URL)

celery_app.conf.update(
    # 只允许 JSON，避免反序列化不可信 Python 对象。
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 任务结果写入业务数据库，不使用 Celery Result Backend。
    task_ignore_result=True,
    result_backend=None,
    # 统一使用 UTC。
    enable_utc=True,
    timezone="UTC",
    # 任务完成后才确认消息；Worker 丢失时让 RabbitMQ 重新投递。
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # 每个 Worker 进程一次只预取一个任务。
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"confirm_publish": True},
    task_queues=(
        Queue(JUDGE_QUEUE, durable=True),
        Queue(AI_QUEUE, durable=True),
        Queue(FILE_QUEUE, durable=True),
    ),
    task_routes={
        JUDGE_SUBMISSION_TASK: {"queue": JUDGE_QUEUE},
        EXECUTE_TEST_DATA_TASK: {"queue": JUDGE_QUEUE},
        GENERATE_PROBLEM_TASK: {"queue": AI_QUEUE},
        GENERATE_TEST_SCRIPT_TASK: {"queue": AI_QUEUE},
        FINALIZE_DATASET_TASK: {"queue": FILE_QUEUE},
    },
    include=(
        "app.tasks.judge_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.file_tasks",
    ),
)


__all__ = ["celery_app"]

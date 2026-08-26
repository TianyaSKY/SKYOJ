"""Prometheus 指标收集器。

已注册指标：
- http_requests_total          Counter  按 method / path / status 标签。
- http_request_duration_seconds Histogram 请求耗时（秒）。
- celery_queue_depth          Gauge    Celery 各队列任务数（通过 celery inspect）。
- submissions_total            Counter  按 problem_type / status 标签。
- judge_duration_seconds      Histogram 判题耗时（秒）。
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


# ---------------------------------------------------------------------------
# HTTP 请求指标（由 FastAPI 中间件写入）
# ---------------------------------------------------------------------------
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ---------------------------------------------------------------------------
# 判题业务指标
# ---------------------------------------------------------------------------
submissions_total = Counter(
    "submissions_total",
    "Total submission attempts",
    ["problem_type", "status"],
)

judge_duration = Histogram(
    "judge_duration_seconds",
    "Judge execution duration in seconds",
    ["problem_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# ---------------------------------------------------------------------------
# Celery 队列深度（通过 celery inspect）
# ---------------------------------------------------------------------------
celery_queue_depth = Gauge(
    "celery_queue_depth",
    "Current number of messages in a Celery queue",
    ["queue"],
)


def refresh_celery_queue_depth() -> None:
    """通过 celery inspect active 估算各队列任务数。"""
    try:
        from celery.app.control import inspect

        active = inspect.active()
        queue_counts: dict[str, int] = {}
        if active:
            for worker_tasks in active.values():
                if isinstance(worker_tasks, list):
                    for task in worker_tasks:
                        if isinstance(task, dict):
                            delivery_info = task.get("delivery_info", {})
                            queue = delivery_info.get("routing_key", "celery")
                            queue_counts[queue] = queue_counts.get(queue, 0) + 1
        # 也尝试 inspect stats 获取更多信息。
        stats = inspect.stats()
        if stats:
            for worker_data in stats.values():
                if isinstance(worker_data, dict):
                    pools = worker_data.get("pool", {})
                    if isinstance(pools, dict):
                        queues = pools.get("queues", [])
                        if isinstance(queues, list):
                            for q in queues:
                                if isinstance(q, str) and q not in queue_counts:
                                    queue_counts[q] = 0
        # 写入 Gauge（即使全是 0 也更新）。
        for queue_name in ("celery", "ai_tasks", "file_tasks"):
            celery_queue_depth.labels(queue=queue_name).set(queue_counts.get(queue_name, 0))
    except Exception:
        for queue_name in ("celery", "ai_tasks", "file_tasks"):
            celery_queue_depth.labels(queue=queue_name).set(-1)


def get_metrics() -> bytes:
    """返回 Prometheus 格式的指标文本。"""
    return generate_latest()


def get_metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST

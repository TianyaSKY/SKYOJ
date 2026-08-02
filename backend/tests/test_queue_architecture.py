"""消息队列与串行执行架构回归测试。"""

from pathlib import Path

from app.messaging.celery_app import celery_app


def test_only_three_durable_queues_and_five_routed_tasks():
    queue_names = {queue.name for queue in celery_app.conf.task_queues}
    assert queue_names == {"judge", "ai", "file"}
    assert set(celery_app.conf.task_routes) == {
        "skyoj.tasks.judge_submission",
        "skyoj.tasks.execute_test_data",
        "skyoj.tasks.generate_problem",
        "skyoj.tasks.generate_test_script",
        "skyoj.tasks.finalize_dataset",
    }


def test_application_code_does_not_create_threads_or_thread_pools():
    app_root = Path(__file__).parents[1] / "app"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in app_root.rglob("*.py")
    )
    for forbidden in (
        "threading.Thread",
        "ThreadPoolExecutor",
        "BackgroundTasks",
        "asyncio.create_task",
    ):
        assert forbidden not in source

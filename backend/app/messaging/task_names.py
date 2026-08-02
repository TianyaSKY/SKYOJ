"""Celery 任务名称。"""

JUDGE_SUBMISSION_TASK = "skyoj.tasks.judge_submission"
EXECUTE_TEST_DATA_TASK = "skyoj.tasks.execute_test_data"
GENERATE_PROBLEM_TASK = "skyoj.tasks.generate_problem"
GENERATE_TEST_SCRIPT_TASK = "skyoj.tasks.generate_test_script"
FINALIZE_DATASET_TASK = "skyoj.tasks.finalize_dataset"

__all__ = [
    "EXECUTE_TEST_DATA_TASK",
    "FINALIZE_DATASET_TASK",
    "GENERATE_PROBLEM_TASK",
    "GENERATE_TEST_SCRIPT_TASK",
    "JUDGE_SUBMISSION_TASK",
]

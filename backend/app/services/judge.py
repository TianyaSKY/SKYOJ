"""judge 业务参数、结果与服务。"""

from __future__ import annotations

import time as time_module
from dataclasses import dataclass
from typing import Optional

from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.judging.acm import run_acm_judge
from app.judging.kaggle import run_kaggle_judge
from app.judging.oop import run_oop_judge
from app.persistence.jobs import AsyncJobRepository
from app.persistence.submission import SubmissionRepository
from app.persistence.unit_of_work import UnitOfWork
from loguru import logger

# 提交状态常量
STATUS_PENDING = "Pending"
STATUS_ACCEPTED = "Accepted"
STATUS_WRONG_ANSWER = "Wrong Answer"
STATUS_TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
STATUS_RUNTIME_ERROR = "Runtime Error"
STATUS_COMPILE_ERROR = "Compile Error"
STATUS_SYSTEM_ERROR = "System Error"


# 题目类型常量
PROBLEM_TYPE_ACM = "acm"
PROBLEM_TYPE_OOP = "oop"
PROBLEM_TYPE_KAGGLE = "kaggle"


# 编程语言常量
LANGUAGE_PYTHON = "python"
LANGUAGE_JAVA = "java"
LANGUAGE_C = "c"
LANGUAGE_CPP = "cpp"


@dataclass(frozen=True)
class JudgeParams:
    """判题参数。"""

    submission_id: int
    problem_type: str
    user_code: str
    problem_id: int
    language: str
    time_limit: int = 1000
    memory_limit: int = 128


@dataclass(frozen=True)
class JudgeResult:
    """判题结果。"""

    status: str
    score: float
    log: str


@dataclass(frozen=True)
class LangConfig:
    """语言编译运行配置。"""

    src: str
    compile: Optional[str]
    run: str


@dataclass(frozen=True)
class SaveScriptParams:
    """保存非 ACM 评测脚本参数。"""

    problem_id: int
    code: str
    problem_type: str
    language: str


@dataclass(frozen=True)
class SaveScriptResult:
    """保存脚本结果。"""

    success: bool
    message: str


def judge_submission(submission_id: int, db) -> None:
    """读取提交并执行判题；该函数只在 Judge Worker 中调用，db 必传。"""
    repository = SubmissionRepository(db)
    submission = repository.get_by_id(submission_id)
    if not submission:
        logger.warning("提交记录不存在，跳过判题 submission_id={}", submission_id)
        return

    final_status = "System Error"
    final_score = 0.0
    final_log = ""
    problem_type = str(submission.problem.type or "acm").lower()

    problem_id = submission.problem_id
    case_results: list[dict] = []
    judge_start = time_module.perf_counter()

    try:
        user_code = submission.code_content or ""
        language = submission.language or "python"
        if problem_type == "acm":
            status, score, log, case_results = run_acm_judge(
                submission_id, user_code, problem_id, language, db=db
            )
        elif problem_type == "oop":
            status, score, log = run_oop_judge(
                submission_id, user_code, problem_id, language, db=db
            )
        elif problem_type == "kaggle":
            status, score, log = run_kaggle_judge(
                submission_id, user_code, problem_id, db=db
            )
        else:
            status, score, log = "System Error", 0, "Unsupported problem type"

        final_status = status
        final_score = score
        final_log = log
    except Exception as exc:
        final_log = f"Judge Error: {str(exc)}"
        logger.exception("判题业务执行异常 submission_id={}", submission_id)
    finally:
        duration = time_module.perf_counter() - judge_start
        try:
            from app.middleware.metrics import judge_duration, submissions_total

            judge_duration.labels(problem_type=problem_type).observe(duration)
            submissions_total.labels(
                problem_type=problem_type, status=final_status
            ).inc()
        except Exception:
            logger.exception("记录判题指标失败 submission_id={}", submission_id)

    from app.persistence.user import WrongBookRepository
    from app.services.wrong_book import WrongBookService

    uow = UnitOfWork(db)
    with uow.transaction():
        repository.update_result(
            submission_id,
            status=final_status,
            score=final_score,
            output_log=final_log,
            case_results=case_results,
        )
        WrongBookService(WrongBookRepository(db), uow=uow).record_judge_result(
            user_id=submission.user_id,
            problem_id=problem_id,
            submission_id=submission_id,
            status=final_status,
        )

    _publish_realtime_result(submission_id, final_status, final_score, final_log)

    if submission is not None and submission.exam_id:
        _invalidate_exam_cache(submission.exam_id)

    if final_status == "Accepted":
        _enqueue_plagiarism_scan(db, problem_id, submission_id)


def _publish_realtime_result(
    submission_id: int, status: str, score: float, output_log: str
) -> None:
    """判题完成后发布实时通知。失败记录日志，不影响主流程。"""
    try:
        from app.clients.redis_client import redis_client

        redis_client.publish(
            f"skyoj:submission:{submission_id}",
            {
                "submission_id": submission_id,
                "status": status,
                "score": score,
                "output_log": output_log or "",
            },
        )
    except Exception as exc:
        logger.warning("实时推送失败 submission_id={} error={}", submission_id, exc)


def _invalidate_exam_cache(exam_id: int) -> None:
    """考试中提交判题后，失效排行榜缓存以保证下一位用户看到最新结果。"""
    try:
        from app.services.exam import invalidate_rank_cache

        invalidate_rank_cache(exam_id)
    except Exception as exc:
        logger.warning("失效考试缓存失败 exam_id={} error={}", exam_id, exc)


def _enqueue_plagiarism_scan(db, problem_id: int, submission_id: int) -> None:
    """判题完成后触发异步查重扫描。"""
    try:
        from app.messaging.queues import JUDGE_QUEUE
        from app.messaging.task_names import SCAN_PLAGIARISM_TASK
        from app.services.async_job import AsyncJobService, CreateAsyncJobParams

        job_service = AsyncJobService(AsyncJobRepository(db), uow=UnitOfWork(db))
        job_service.enqueue(
            CreateAsyncJobParams(
                task_name=SCAN_PLAGIARISM_TASK,
                queue=JUDGE_QUEUE,
                payload={"problem_id": problem_id, "min_similarity": 0.3},
                dedupe_key=f"plagiarism-scan:{problem_id}:{submission_id}",
                max_attempts=1,
            )
        )
    except Exception as exc:
        logger.warning("查重任务投递失败 problem_id={} error={}", problem_id, exc)


def save_non_acm_script(
    problem_id: int,
    code: str,
    problem_type: str,
    language: str | None,
    *,
    storage: ProblemTestCaseStorageClient | None = None,
) -> tuple[bool, str]:
    """编排非 ACM 判题脚本保存，文件操作由存储客户端负责。"""
    try:
        filename = (storage or ProblemTestCaseStorageClient()).save_script(
            problem_id,
            code,
            language,
        )
        return True, f"Script saved as {filename} for {problem_type} problem."
    except OSError:
        logger.exception(
            "保存非 ACM 测试脚本失败 problem_id={} problem_type={}",
            problem_id,
            problem_type,
        )
        return False, "测试脚本保存失败"

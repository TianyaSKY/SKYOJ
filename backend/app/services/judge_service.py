"""判题编排：按题目类型分发到各模式判题实现。"""

import os

from loguru import logger

from app.repositories.submission_repository import SubmissionRepository
from app.services.acm import run_acm_judge
from app.services.kaggle import run_kaggle_judge
from app.services.oop import run_oop_judge


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

    try:
        problem_type = str(submission.problem.type or "acm").lower()
        user_code = submission.code_content or ""
        problem_id = submission.problem_id
        language = submission.language or "python"
        case_results: list[dict] = []
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

    repository.update_result(
        submission_id,
        status=final_status,
        score=final_score,
        output_log=final_log,
        case_results=case_results,
    )
    db.commit()

    # === 错题本更新 ===
    if submission is not None:
        try:
            from app.services.wrong_book_service import WrongBookService
            wb = WrongBookService(db)
            wb.on_judge_complete(
                user_id=submission.user_id,
                problem_id=problem_id,
                submission_id=submission_id,
                status=final_status,
            )
        except Exception as exc:
            logger.warning("错题本更新失败 submission_id={} error={}", submission_id, exc)

    _publish_realtime_result(submission_id, final_status, final_score, final_log)

    if submission is not None and submission.exam_id:
        _invalidate_exam_cache(submission.exam_id)

    if final_status == "Accepted":
        _enqueue_plagiarism_scan(db, problem_id)


def _publish_realtime_result(submission_id: int, status: str, score: float, output_log: str) -> None:
    """判题完成后发布实时通知。失败静默，不影响主流程。"""
    try:
        from app.utils.realtime import publish_submission_result
        publish_submission_result(submission_id, status, score, output_log)
    except Exception as exc:
        logger.warning("实时推送失败 submission_id={} error={}", submission_id, exc)


def _invalidate_exam_cache(exam_id: int) -> None:
    """考试中提交判题后，失效排行榜缓存以保证下一位用户看到最新结果。"""
    try:
        from app.utils.exam_cache import invalidate_rank_cache
        invalidate_rank_cache(exam_id)
    except Exception as exc:
        logger.warning("失效考试缓存失败 exam_id={} error={}", exam_id, exc)


def _enqueue_plagiarism_scan(db, problem_id: int) -> None:
    """判题完成后触发异步查重扫描。"""
    try:
        from app.domain.async_job import CreateAsyncJobParams
        from app.messaging.queues import JUDGE_QUEUE
        from app.messaging.task_names import SCAN_PLAGIARISM_TASK
        from app.services.async_job_service import AsyncJobService

        job_service = AsyncJobService.from_session(db)
        job_service.enqueue(
            CreateAsyncJobParams(
                task_name=SCAN_PLAGIARISM_TASK,
                queue=JUDGE_QUEUE,
                payload={"problem_id": problem_id, "min_similarity": 0.3},
                dedupe_key=f"plagiarism-scan:{problem_id}",
                max_attempts=1,
            )
        )
    except Exception as exc:
        logger.warning("查重任务投递失败 problem_id={} error={}", problem_id, exc)


def save_non_acm_script(problem_id, code, problem_type, language):
    """封装非 ACM 类型的脚本保存逻辑"""
    problem_dir = os.path.join("uploads/problems", str(problem_id))
    os.makedirs(problem_dir, exist_ok=True)

    lang_map = {
        "python": "main.py",
        "c": "main.c",
        "cpp": "main.cpp",
        "java": "Main.java",
    }

    filename = lang_map.get((language or "python").lower(), "main.py")
    file_path = os.path.join(problem_dir, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return True, f"Script saved as {filename} for {problem_type} problem."
    except Exception as exc:
        logger.exception(
            "保存非 ACM 测试脚本失败 problem_id={} problem_type={}",
            problem_id,
            problem_type,
        )
        return False, str(exc)

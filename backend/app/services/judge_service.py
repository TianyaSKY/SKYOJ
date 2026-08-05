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

    try:
        problem_type = str(submission.problem.type or "acm").lower()
        user_code = submission.code_content or ""
        problem_id = submission.problem_id
        language = submission.language or "python"
        if problem_type == "acm":
            status, score, log = run_acm_judge(
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

        repository.update_result(
            submission_id, status=status, score=score, output_log=log
        )
    except Exception as exc:
        repository.update_result(
            submission_id,
            status="System Error",
            score=0,
            output_log=f"Judge Error: {str(exc)}",
        )
        logger.exception("判题业务执行异常 submission_id={}", submission_id)

    db.commit()


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

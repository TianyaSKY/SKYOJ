"""AI Worker 任务：出题和测试脚本生成。"""

from typing import Any, Callable

from loguru import logger

from app.clients.llm_client import LlmClient
from app.database import SessionLocal
from app.domain.async_job import GENERATE_PROBLEM_TASK, GENERATE_TEST_SCRIPT_TASK
from app.messaging.celery_app import celery_app
from app.repositories.ai_draft_repository import AiDraftRepository
from app.repositories.async_job_repository import AsyncJobRepository
from app.repositories.problem_repository import ProblemRepository
from app.services.async_job_service import AsyncJobService


@celery_app.task(name=GENERATE_PROBLEM_TASK, ignore_result=True)
def generate_problem(job_id: int) -> None:
    """执行 AI 出题任务。"""
    _execute_ai_job(job_id, _run_problem_generation, GENERATE_PROBLEM_TASK)


@celery_app.task(name=GENERATE_TEST_SCRIPT_TASK, ignore_result=True)
def generate_test_script(job_id: int) -> None:
    """执行 AI 测试脚本生成任务。"""
    _execute_ai_job(job_id, _run_test_script_generation, GENERATE_TEST_SCRIPT_TASK)


def _execute_ai_job(
    job_id: int,
    handler: Callable[[AiDraftRepository, ProblemRepository, int, dict[str, Any]], None],
    task_name: str,
) -> None:
    db = SessionLocal()
    job_service = AsyncJobService.from_session(db)
    started = job_service.start_job(
        job_id,
        lease_seconds=job_service.lease_seconds(task_name),
    )
    if started is None:
        db.close()
        return

    draft_id: int | None = None
    draft_repository = AiDraftRepository(db)
    try:
        job = AsyncJobRepository(db).get_by_id(job_id)
        if job is None:
            raise ValueError(f"异步任务不存在: {job_id}")
        payload = job_service.parse_payload(job.payload)
        draft_id = int(payload["draft_id"])
        draft_repository.mark_running(draft_id)
        handler(
            draft_repository,
            ProblemRepository(db),
            draft_id,
            AiDraftRepository.parse_json_field(
                draft_repository.get_by_id(draft_id).request_payload
            ),
        )
        job_service.complete_job(job_id)
    except Exception as exc:
        logger.exception("AI 任务执行失败 job_id={} draft_id={}", job_id, draft_id)
        result = job_service.fail_job(job_id, str(exc))
        if draft_id is not None and result is not None and result.status == "failed":
            draft_repository.mark_failed(draft_id, str(exc))
    finally:
        db.close()


def _run_problem_generation(
    draft_repository: AiDraftRepository,
    problem_repository: ProblemRepository,
    draft_id: int,
    request: dict[str, Any],
) -> None:
    """调用 LLM 生成题目并写入草稿箱。"""
    del problem_repository
    background = str(request.get("background", "")).strip()
    difficulty = str(request.get("difficulty", "简单")).strip() or "简单"
    system_setting = (
        "你是一个专业的算法竞赛出题人。请根据用户提供的背景 and 难度，设计一道高质量的编程题目。\n"
        "平台支持三种模式：\n"
        "1. ACM 模式：标准 I/O，严格文本比对。\n"
        "2. OOP 模式：实现特定接口/类，运行单元测试。\n"
        "3. Kaggle 模式：提交预测结果 CSV 文件，基于 Metric 评分。\n"
        "请根据题目性质选择最合适的模式。题目内容必须使用 Markdown 格式，包含："
        "题目描述、输入格式、输出格式、样例输入、样例输出、提示/说明。"
    )
    prompt = f"题目背景: {background}\n难度: {difficulty}"
    output_format = {
        "title": "题目名称",
        "content": "Markdown 格式的题目内容",
        "template_code": "该题目的初始代码模板（可选）",
        "type": "acm/oop/kaggle",
        "language": "建议的编程语言 (python/cpp/java/c)",
        "time_limit": 1000,
        "memory_limit": 128,
    }

    result = LlmClient().chat_json(
        system_setting=system_setting,
        prompt=prompt,
        output_format=output_format,
    )
    title = str(result.get("title") or "AI 生成题目").strip() or "AI 生成题目"
    draft_repository.mark_success(draft_id, result_payload=result, title=title)
    logger.info("AI 出题完成 draft_id={} title={}", draft_id, title)


def _run_test_script_generation(
    draft_repository: AiDraftRepository,
    problem_repository: ProblemRepository,
    draft_id: int,
    request: dict[str, Any],
) -> None:
    """调用 LLM 生成 ACM/OOP/Kaggle 测试脚本。"""
    problem_id = int(request["problem_id"])
    direction = str(request.get("direction") or "").strip()
    problem = problem_repository.get_by_id(problem_id)
    if problem is None:
        raise ValueError(f"题目不存在: {problem_id}")

    problem_type = problem.type or "acm"
    language = problem.language or "python"
    problem_snapshot = {
        "id": problem.id,
        "title": problem.title,
        "content": problem.content,
        "type": problem_type,
        "language": language,
        "time_limit": problem.time_limit,
        "memory_limit": problem.memory_limit,
        "template_code": problem.template_code or "",
    }
    mode_configs = {
        "acm": {
            "role": "测试数据生成专家",
            "task": "编写一个 Python 脚本，用于生成随机的输入数据（.in）和对应的标准答案（.out）。并直接放置在原始文件夹下",
            "rule": "脚本应根据题目约束生成多组测试数据（含边界与典型情况），数量与数据范围由题目描述自行合理推断。",
        },
        "oop": {
            "role": "自动化测试专家",
            "task": "编写一个单元测试脚本，用于验证学生提交的代码实现。",
            "rule": (
                "【重要】脚本必须包含/导入学生的代码。\n"
                '- 对于 C++: 使用 #include "solution.cpp"\n'
                "- 对于 Java: 假设学生类在同包下直接调用，或使用 import Solution;\n"
                "- 对于 Python: 使用 from solution import *\n"
                "严禁在脚本中自行实现题目要求的类，必须测试外部导入的实现。最后一行必须只打印一个 0-100 的整数分数。"
            ),
        },
        "kaggle": {
            "role": "数据科学竞赛裁判",
            "task": "编写一个评估脚本，用于对比学生的预测结果 and 已有的标准答案。",
            "rule": (
                "【重要】严禁在脚本中生成随机数据 or 创建 truth.csv。"
                "脚本应假设当前目录下已存在 truth.csv（老师上传）和 submission.csv（学生上传）。"
                "脚本只需读取这两个文件，计算指标（如 Accuracy/MSE），最后一行只打印一个 0-100 的整数分数。"
            ),
        },
    }
    config = mode_configs.get(problem_type, mode_configs["acm"])
    script_language = language if problem_type == "oop" else "python"
    system_setting = (
        f"你是一个专业的{config['role']}。\n"
        f"当前题目类型：{problem_type.upper()}\n"
        f"题目目标语言：{language}\n\n"
        f"任务目标：{config['task']}\n\n"
        "具体要求：\n"
        f"1. 语言：使用 {script_language}。\n"
        f"2. 逻辑：{config['rule']}\n"
        "3. 输出控制：你可以打印调试日志，但脚本执行的最后一行输出必须且只能是一个整数（0-100），代表得分。\n"
        "4. 依赖：尽量使用基础库（如 csv, math, json），如果使用 pandas 或 sklearn，请确保逻辑简洁。"
    )
    prompt = f"题目内容: {problem_snapshot}\n生成要求: {direction or '执行标准评估逻辑'}"
    output_format = {
        "code": "生成的完整代码字符串",
        "language": "脚本使用的编程语言 (python/java/cpp/c)",
    }
    result = LlmClient().chat_json(
        system_setting=system_setting,
        prompt=prompt,
        output_format=output_format,
    )
    payload = {
        "code": str(result.get("code") or ""),
        "language": str(result.get("language") or (language if problem_type == "oop" else "python")),
        "problem_id": problem_id,
        "problem_type": problem_type,
        "problem_title": problem.title,
        "direction": direction,
    }
    draft_repository.mark_success(
        draft_id,
        result_payload=payload,
        title=f"测例脚本 · {problem.title}",
    )
    logger.info("测例脚本生成完成 draft_id={} problem_id={}", draft_id, problem_id)


__all__ = ["generate_problem", "generate_test_script"]

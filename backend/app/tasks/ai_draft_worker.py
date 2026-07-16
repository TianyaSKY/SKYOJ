"""AI 草稿后台任务实现。"""

from typing import Any

from loguru import logger

from app.clients.llm_client import LlmClient
from app.database import SessionLocal
from app.domain.ai_draft import (
    TASK_PROBLEM_GENERATION,
    TASK_TEST_DATA_EXECUTION,
    TASK_TEST_SCRIPT_GENERATION,
)
from app.repositories.ai_draft_repository import AiDraftRepository
from app.repositories.problem_repository import ProblemRepository
from app.services.judge_service import save_non_acm_script
from app.services.test_gen_service import run_test_generation


def process_ai_draft(draft_id: int) -> None:
    """根据草稿类型执行对应后台逻辑。"""
    db = SessionLocal()
    try:
        draft_repo = AiDraftRepository(db)
        draft = draft_repo.get_by_id(draft_id)
        if draft is None:
            logger.warning("草稿不存在，跳过执行: draft_id={}", draft_id)
            return

        draft_repo.mark_running(draft_id)
        request = AiDraftRepository.parse_json_field(draft.request_payload)
        task_type = draft.task_type

        if task_type == TASK_PROBLEM_GENERATION:
            _run_problem_generation(draft_repo, draft_id, request)
        elif task_type == TASK_TEST_SCRIPT_GENERATION:
            problem_repo = ProblemRepository(db)
            _run_test_script_generation(draft_repo, problem_repo, draft_id, request)
        elif task_type == TASK_TEST_DATA_EXECUTION:
            _run_test_data_execution(draft_repo, draft_id, request)
        else:
            draft_repo.mark_failed(draft_id, f"未知任务类型: {task_type}")
    except Exception as exc:
        logger.exception("处理草稿失败 draft_id={}: {}", draft_id, str(exc))
        try:
            AiDraftRepository(db).mark_failed(draft_id, str(exc))
        except Exception:
            logger.exception("写入草稿失败状态时再次异常 draft_id={}", draft_id)
    finally:
        db.close()


def _run_problem_generation(
    draft_repo: AiDraftRepository,
    draft_id: int,
    request: dict[str, Any],
) -> None:
    """执行 AI 出题。"""
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

    llm = LlmClient()
    result = llm.chat_json(
        system_setting=system_setting,
        prompt=prompt,
        output_format=output_format,
    )
    title = str(result.get("title") or "AI 生成题目").strip() or "AI 生成题目"
    draft_repo.mark_success(draft_id, result_payload=result, title=title)
    logger.info("AI 出题完成 draft_id={} title={}", draft_id, title)


def _run_test_script_generation(
    draft_repo: AiDraftRepository,
    problem_repo: ProblemRepository,
    draft_id: int,
    request: dict[str, Any],
) -> None:
    """执行测例/评估脚本生成。"""
    problem_id = int(request["problem_id"])
    direction = str(request.get("direction") or "").strip()
    count = int(request.get("count") or 10)
    range_info = str(request.get("range_info") or "").strip()

    problem = problem_repo.get_by_id(problem_id)
    if problem is None:
        draft_repo.mark_failed(draft_id, f"题目不存在: {problem_id}")
        return

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
            "task": (
                "编写一个 Python 脚本，用于生成随机的输入数据（.in）和对应的标准答案（.out）。"
                "并直接放置在原始文件夹下"
            ),
            "rule": f"脚本应循环生成{count}组测试数据的测试点文件。",
        },
        "oop": {
            "role": "自动化测试专家",
            "task": "编写一个单元测试脚本，用于验证学生提交的代码实现。",
            "rule": (
                "【重要】脚本必须包含/导入学生的代码。\n"
                '- 对于 C++: 使用 #include "solution.cpp"\n'
                "- 对于 Java: 假设学生类在同包下直接调用，或使用 import Solution;\n"
                "- 对于 Python: 使用 from solution import *\n"
                "严禁在脚本中自行实现题目要求的类，必须测试外部导入的实现。"
                "最后一行必须只打印一个 0-100 的整数分数。"
            ),
        },
        "kaggle": {
            "role": "数据科学竞赛裁判",
            "task": "编写一个评估脚本，用于对比学生的预测结果 and 已有的标准答案。",
            "rule": (
                "【重要】严禁在脚本中生成随机数据 or 创建 truth.csv。"
                "脚本应假设当前目录下已存在 truth.csv（老师上传）和 submission.csv（学生上传）。"
                "脚本只需读取这两个文件，计算指标（如 Accuracy/MSE），"
                "最后一行只打印一个 0-100 的整数分数。"
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
        "3. 输出控制：你可以打印调试日志，但脚本执行的最后一行输出必须且只能是一个整数"
        "（0-100），代表得分。\n"
        "4. 依赖：尽量使用基础库（如 csv, math, json），如果使用 pandas 或 sklearn，"
        "请确保逻辑简洁。"
    )
    prompt = (
        f"题目内容: {problem_snapshot}\n"
        f"生成要求: {direction or '执行标准评估逻辑'}\n"
        f"数据范围/参考: {range_info or '无'}"
    )
    output_format = {
        "code": "生成的完整代码字符串",
        "language": "脚本使用的编程语言 (python/java/cpp/c)",
    }

    llm = LlmClient()
    result = llm.chat_json(
        system_setting=system_setting,
        prompt=prompt,
        output_format=output_format,
    )
    code = str(result.get("code") or "")
    result_language = str(
        result.get("language")
        or (language if problem_type == "oop" else "python")
    )
    payload = {
        "code": code,
        "language": result_language,
        "problem_id": problem_id,
        "problem_type": problem_type,
        "problem_title": problem.title,
        "count": count,
        "direction": direction,
        "range_info": range_info,
    }
    title = f"测例脚本 · {problem.title}"
    draft_repo.mark_success(draft_id, result_payload=payload, title=title)
    logger.info("测例脚本生成完成 draft_id={} problem_id={}", draft_id, problem_id)


def _run_test_data_execution(
    draft_repo: AiDraftRepository,
    draft_id: int,
    request: dict[str, Any],
) -> None:
    """执行测例生成脚本或保存非 ACM 脚本。"""
    problem_id = int(request["problem_id"])
    code = str(request.get("code") or "")
    problem_type = str(request.get("problem_type") or request.get("type") or "acm")
    language = str(request.get("language") or "python")

    if not code.strip():
        draft_repo.mark_failed(draft_id, "执行代码为空")
        return

    if problem_type != "acm":
        success, message = save_non_acm_script(problem_id, code, problem_type, language)
    else:
        success, message = run_test_generation(problem_id, code)

    if not success:
        draft_repo.mark_failed(draft_id, message)
        return

    payload = {
        "message": message,
        "problem_id": problem_id,
        "problem_type": problem_type,
        "language": language,
    }
    title = f"测例执行 · 题目 #{problem_id}"
    draft_repo.mark_success(draft_id, result_payload=payload, title=title)
    logger.info("测例执行完成 draft_id={} problem_id={}", draft_id, problem_id)

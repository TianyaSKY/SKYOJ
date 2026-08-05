"""AI 草稿箱业务服务。"""

from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.clients.llm_client import LlmClient
from app.messaging.task_names import (
    GENERATE_PROBLEM_TASK,
    GENERATE_TEST_SCRIPT_TASK,
)
from app.domain.ai_draft import (
    STATUS_PENDING,
    STATUS_SUCCESS,
    TASK_PROBLEM_GENERATION,
    TASK_TEST_DATA_EXECUTION,
    TASK_TEST_SCRIPT_GENERATION,
    AiDraftDetail,
    AiDraftStats,
    AiDraftSummary,
    ApplyProblemDraftResult,
    SubmitProblemGenerationParams,
    SubmitTaskResult,
    SubmitTestDataExecutionParams,
    SubmitTestScriptGenerationParams,
)
from app.domain.ai_prompts import (
    PROBLEM_GENERATION_OUTPUT_FORMAT,
    PROBLEM_GENERATION_SYSTEM_SETTING,
    TEST_SCRIPT_MODE_CONFIGS,
    TEST_SCRIPT_OUTPUT_FORMAT,
)
from app.domain.errors import (
    InvalidStateError,
    LlmConfigError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.mappers import from_ai_draft_orm
from app.repositories.ai_draft_repository import AiDraftRepository
from app.repositories.problem_repository import ProblemRepository
from app.services.async_job_service import AsyncJobService


class AiDraftService:
    """AI 异步出题 / 测例生成与草稿箱业务。"""

    # 草稿任务类型 → 入队方法（dedupe 前缀由各 enqueue 方法决定，保持不变）
    _TASK_TYPE_TO_ENQUEUE = {
        TASK_PROBLEM_GENERATION: "enqueue_ai_draft",
        TASK_TEST_SCRIPT_GENERATION: "enqueue_ai_draft",
        TASK_TEST_DATA_EXECUTION: "enqueue_test_data_execution",
    }
    _AI_TASK_TYPE_TO_NAME = {
        TASK_PROBLEM_GENERATION: GENERATE_PROBLEM_TASK,
        TASK_TEST_SCRIPT_GENERATION: GENERATE_TEST_SCRIPT_TASK,
    }

    def __init__(
        self,
        draft_repository: AiDraftRepository,
        problem_repository: ProblemRepository,
        job_service: AsyncJobService,
        llm_client: Optional[LlmClient] = None,
    ) -> None:
        self._drafts = draft_repository
        self._problems = problem_repository
        self._job_service = job_service
        self._llm_client = llm_client or LlmClient()

    def _ensure_llm_ready(self) -> None:
        if not self._llm_client.is_configured():
            raise LlmConfigError(
                "LLM 环境变量未完整配置，请设置 LLM_API_KEY、LLM_API_URL、LLM_MODEL_NAME"
            )

    def submit_problem_generation(
        self,
        params: SubmitProblemGenerationParams,
    ) -> SubmitTaskResult:
        """提交 AI 出题异步任务。"""
        self._ensure_llm_ready()
        background = params.background.strip()
        if not background:
            raise InvalidStateError("题目背景不能为空")

        difficulty = (params.difficulty or "简单").strip() or "简单"
        title = f"出题中 · {background[:40]}"
        request_payload = {
            "background": background,
            "difficulty": difficulty,
        }
        draft = self._drafts.create(
            user_id=params.user_id,
            task_type=TASK_PROBLEM_GENERATION,
            title=title,
            request_payload=request_payload,
            status=STATUS_PENDING,
        )
        self._enqueue_draft_job(draft)
        logger.info(
            "已提交 AI 出题任务 draft_id={} user_id={}",
            draft.id,
            params.user_id,
        )
        return SubmitTaskResult(
            draft_id=draft.id,
            status=draft.status,
            task_type=draft.task_type,
            title=draft.title,
        )

    def submit_test_script_generation(
        self,
        params: SubmitTestScriptGenerationParams,
    ) -> SubmitTaskResult:
        """提交测例脚本生成异步任务。"""
        self._ensure_llm_ready()
        problem = self._problems.get_by_id(params.problem_id)
        if problem is None:
            raise ResourceNotFoundError(f"题目不存在: {params.problem_id}")

        title = f"生成脚本中 · {problem.title}"
        request_payload = {
            "problem_id": params.problem_id,
            "direction": (params.direction or "").strip(),
        }
        draft = self._drafts.create(
            user_id=params.user_id,
            task_type=TASK_TEST_SCRIPT_GENERATION,
            title=title,
            request_payload=request_payload,
            problem_id=params.problem_id,
            status=STATUS_PENDING,
        )
        self._enqueue_draft_job(draft)
        logger.info(
            "已提交测例脚本任务 draft_id={} problem_id={}",
            draft.id,
            params.problem_id,
        )
        return SubmitTaskResult(
            draft_id=draft.id,
            status=draft.status,
            task_type=draft.task_type,
            title=draft.title,
        )

    def submit_test_data_execution(
        self,
        params: SubmitTestDataExecutionParams,
    ) -> SubmitTaskResult:
        """提交测例执行 / 脚本落盘异步任务。"""
        problem = self._problems.get_by_id(params.problem_id)
        if problem is None:
            raise ResourceNotFoundError(f"题目不存在: {params.problem_id}")

        code = (params.code or "").strip()
        if not code:
            raise InvalidStateError("执行代码不能为空")

        problem_type = (params.problem_type or problem.type or "acm").strip()
        language = (params.language or problem.language or "python").strip()
        title = f"执行测例中 · {problem.title}"
        request_payload = {
            "problem_id": params.problem_id,
            "code": code,
            "problem_type": problem_type,
            "type": problem_type,
            "language": language,
            "source_draft_id": params.source_draft_id,
        }
        draft = self._drafts.create(
            user_id=params.user_id,
            task_type=TASK_TEST_DATA_EXECUTION,
            title=title,
            request_payload=request_payload,
            problem_id=params.problem_id,
            status=STATUS_PENDING,
        )
        self._enqueue_draft_job(draft)
        logger.info(
            "已提交测例执行任务 draft_id={} problem_id={}",
            draft.id,
            params.problem_id,
        )
        return SubmitTaskResult(
            draft_id=draft.id,
            status=draft.status,
            task_type=draft.task_type,
            title=draft.title,
        )

    def _enqueue_draft_job(self, draft) -> None:
        """创建异步任务；按草稿任务类型选择入队方法。"""
        enqueue_name = self._TASK_TYPE_TO_ENQUEUE.get(draft.task_type)
        if enqueue_name is None:
            raise ValueError(f"不支持的草稿任务类型: {draft.task_type}")
        if enqueue_name == "enqueue_ai_draft":
            self._job_service.enqueue_ai_draft(
                draft.id, self._AI_TASK_TYPE_TO_NAME[draft.task_type]
            )
        else:
            self._job_service.enqueue_test_data_execution(draft.id)

    def generate_problem(self, draft_id: int, db: Session) -> dict:
        """执行 AI 出题任务（Worker 内调用）。"""
        draft = self._drafts.get_by_id(draft_id)
        if draft is None:
            raise ValueError(f"AI 草稿不存在: {draft_id}")
        self._drafts.mark_running(draft_id)
        request = AiDraftRepository.parse_json_field(draft.request_payload)

        background = str(request.get("background", "")).strip()
        difficulty = str(request.get("difficulty", "简单")).strip() or "简单"
        prompt = f"题目背景: {background}\n难度: {difficulty}"

        result = self._llm_client.chat_json(
            system_setting=PROBLEM_GENERATION_SYSTEM_SETTING,
            prompt=prompt,
            output_format=PROBLEM_GENERATION_OUTPUT_FORMAT,
        )
        title = str(result.get("title") or "AI 生成题目").strip() or "AI 生成题目"
        self._drafts.mark_success(draft_id, result_payload=result, title=title)
        logger.info("AI 出题完成 draft_id={} title={}", draft_id, title)
        return result

    def generate_test_script(self, draft_id: int, db: Session) -> dict:
        """执行测例脚本生成任务（Worker 内调用）。"""
        draft = self._drafts.get_by_id(draft_id)
        if draft is None:
            raise ValueError(f"AI 草稿不存在: {draft_id}")
        self._drafts.mark_running(draft_id)
        request = AiDraftRepository.parse_json_field(draft.request_payload)

        problem_id = int(request["problem_id"])
        direction = str(request.get("direction") or "").strip()
        problem = self._problems.get_by_id(problem_id)
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
        config = TEST_SCRIPT_MODE_CONFIGS.get(problem_type, TEST_SCRIPT_MODE_CONFIGS["acm"])
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

        result = self._llm_client.chat_json(
            system_setting=system_setting,
            prompt=prompt,
            output_format=TEST_SCRIPT_OUTPUT_FORMAT,
        )
        payload = {
            "code": str(result.get("code") or ""),
            "language": str(
                result.get("language")
                or (language if problem_type == "oop" else "python")
            ),
            "problem_id": problem_id,
            "problem_type": problem_type,
            "problem_title": problem.title,
            "direction": direction,
        }
        self._drafts.mark_success(
            draft_id,
            result_payload=payload,
            title=f"测例脚本 · {problem.title}",
        )
        logger.info("测例脚本生成完成 draft_id={} problem_id={}", draft_id, problem_id)
        return payload

    def list_drafts(
        self,
        user_id: int,
        *,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[AiDraftSummary]:
        """列出当前用户草稿。"""
        drafts = self._drafts.list_by_user(
            user_id,
            status=status,
            task_type=task_type,
            limit=limit,
        )
        return [from_ai_draft_orm(d) for d in drafts]

    def get_draft(self, user_id: int, draft_id: int) -> AiDraftDetail:
        """获取草稿详情。"""
        draft = self._require_owned_draft(user_id, draft_id)
        return from_ai_draft_orm(draft, detail=True)

    def delete_draft(self, user_id: int, draft_id: int) -> None:
        """删除草稿。"""
        draft = self._require_owned_draft(user_id, draft_id)
        if draft.status in ("pending", "running"):
            raise InvalidStateError("任务进行中，暂不可删除，请稍后再试")
        self._drafts.delete(draft)
        logger.info("已删除草稿 draft_id={} user_id={}", draft_id, user_id)

    def get_stats(self, user_id: int) -> AiDraftStats:
        """草稿箱统计。"""
        raw = self._drafts.count_stats(user_id)
        return AiDraftStats(
            total=raw["total"],
            pending=raw["pending"],
            running=raw["running"],
            success=raw["success"],
            failed=raw["failed"],
            unconsumed_success=raw["unconsumed_success"],
        )

    def apply_problem_draft(
        self,
        user_id: int,
        draft_id: int,
    ) -> ApplyProblemDraftResult:
        """将成功的出题草稿创建为正式题目。"""
        draft = self._require_owned_draft(user_id, draft_id)
        if draft.task_type != TASK_PROBLEM_GENERATION:
            raise InvalidStateError("仅出题草稿可以创建正式题目")
        if draft.status != STATUS_SUCCESS:
            raise InvalidStateError("仅成功完成的草稿可以应用")
        if draft.consumed_at is not None:
            raise InvalidStateError("该草稿已创建过正式题目")

        result = AiDraftRepository.parse_json_field(draft.result_payload)
        title = str(result.get("title") or "").strip()
        content = str(result.get("content") or "").strip()
        if not title or not content:
            raise InvalidStateError("草稿结果缺少 title 或 content，无法创建题目")

        language = str(result.get("language") or "python").strip().lower()
        if language not in {"python", "java", "c", "cpp"}:
            language = "python"
        problem_type = str(result.get("type") or "acm").strip().lower()
        if problem_type not in {"acm", "oop", "kaggle"}:
            problem_type = "acm"

        try:
            time_limit = int(result.get("time_limit") or 1000)
        except (TypeError, ValueError):
            time_limit = 1000
        try:
            memory_limit = int(result.get("memory_limit") or 128)
        except (TypeError, ValueError):
            memory_limit = 128

        problem = self._problems.create(
            title=title,
            content=content,
            language=language,
            problem_type=problem_type,
            time_limit=max(100, time_limit),
            memory_limit=max(32, memory_limit),
            template_code=str(result.get("template_code") or ""),
        )
        self._drafts.mark_consumed(draft_id)
        logger.info(
            "出题草稿已应用 draft_id={} problem_id={}",
            draft_id,
            problem.id,
        )
        return ApplyProblemDraftResult(
            problem_id=problem.id,
            draft_id=draft_id,
            title=problem.title,
        )

    def _require_owned_draft(self, user_id: int, draft_id: int):
        draft = self._drafts.get_by_id(draft_id)
        if draft is None:
            raise ResourceNotFoundError(f"草稿不存在: {draft_id}")
        if draft.user_id != user_id:
            raise PermissionDeniedError("无权访问该草稿")
        return draft

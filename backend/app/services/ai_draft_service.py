"""AI 草稿箱业务服务。"""

from typing import Optional

from loguru import logger

from app.clients.llm_client import LlmClient
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
from app.domain.errors import (
    InvalidStateError,
    LlmConfigError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.repositories.ai_draft_repository import AiDraftRepository
from app.repositories.problem_repository import ProblemRepository
from app.tasks.ai_draft_worker import process_ai_draft
from app.tasks.queue import ThreadTaskQueue


class AiDraftService:
    """AI 异步出题 / 测例生成与草稿箱业务。"""

    def __init__(
        self,
        draft_repository: AiDraftRepository,
        problem_repository: ProblemRepository,
        task_queue: ThreadTaskQueue,
        llm_client: Optional[LlmClient] = None,
    ) -> None:
        self._drafts = draft_repository
        self._problems = problem_repository
        self._task_queue = task_queue
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
        self._task_queue.enqueue(process_ai_draft, draft.id)
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

        count = params.count if params.count and params.count > 0 else 10
        if count > 50:
            raise InvalidStateError("测试点个数不能超过 50")

        title = f"生成脚本中 · {problem.title}"
        request_payload = {
            "problem_id": params.problem_id,
            "direction": (params.direction or "").strip(),
            "count": count,
            "range_info": (params.range_info or "").strip(),
        }
        draft = self._drafts.create(
            user_id=params.user_id,
            task_type=TASK_TEST_SCRIPT_GENERATION,
            title=title,
            request_payload=request_payload,
            problem_id=params.problem_id,
            status=STATUS_PENDING,
        )
        self._task_queue.enqueue(process_ai_draft, draft.id)
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
        self._task_queue.enqueue(process_ai_draft, draft.id)
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
        return [self._to_summary(d) for d in drafts]

    def get_draft(self, user_id: int, draft_id: int) -> AiDraftDetail:
        """获取草稿详情。"""
        draft = self._require_owned_draft(user_id, draft_id)
        return self._to_detail(draft)

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

    @staticmethod
    def _to_summary(draft) -> AiDraftSummary:
        return AiDraftSummary(
            id=draft.id,
            task_type=draft.task_type,
            status=draft.status,
            title=draft.title or "",
            problem_id=draft.problem_id,
            error_message=draft.error_message,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            consumed_at=draft.consumed_at,
        )

    @staticmethod
    def _to_detail(draft) -> AiDraftDetail:
        return AiDraftDetail(
            id=draft.id,
            task_type=draft.task_type,
            status=draft.status,
            title=draft.title or "",
            problem_id=draft.problem_id,
            request_payload=AiDraftRepository.parse_json_field(draft.request_payload),
            result_payload=AiDraftRepository.parse_json_field(draft.result_payload),
            error_message=draft.error_message,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            consumed_at=draft.consumed_at,
        )

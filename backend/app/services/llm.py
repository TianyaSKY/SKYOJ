"""llm 业务参数、结果与服务。"""

from __future__ import annotations

from app.core.errors import ExternalServiceError, LlmConfigError, PermissionDeniedError
from app.core.json import JsonObjectResult, JsonValue
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AskLlmParams:
    """请求 LLM 对话的参数。"""

    system_setting: str
    prompt: str
    requester_role: str
    output_format: Optional[dict[str, JsonValue]] = None
    # 若提供，AI 答疑时自动带入该提交代码与判题结果作为上下文。
    context_submission_id: Optional[int] = None


from app.clients.llm_client import LlmClient
from app.persistence.submission import SubmissionRepository


class LlmFacadeService:
    """编排同步 LLM 对话；耗时脚本任务由 Judge Worker 执行。"""

    def __init__(
        self, llm_client: LlmClient, submission_repository: SubmissionRepository
    ) -> None:
        self._llm_client = llm_client
        self._submission_repository = submission_repository

    def ask(self, params: AskLlmParams) -> JsonObjectResult:
        """调用配置好的 LLM 客户端。"""
        self._require_teacher(params.requester_role)
        if not self._llm_client.is_configured():
            raise LlmConfigError("LLM 环境变量未完整配置")
        try:
            final_system = self._enrich_system(params)
            return JsonObjectResult(
                self._llm_client.chat_json(
                    system_setting=final_system,
                    prompt=params.prompt,
                    output_format=params.output_format,
                )
            )
        except RuntimeError as exc:
            raise ExternalServiceError(str(exc)) from exc

    def ask_stream(self, params: AskLlmParams) -> Iterator[str]:
        """SSE 流式调用 LLM，返回生成器。"""
        self._require_teacher(params.requester_role)
        if not self._llm_client.is_configured():
            raise LlmConfigError("LLM 环境变量未完整配置")
        final_system = self._enrich_system(params)
        return self._llm_client.chat_stream(
            system_setting=final_system,
            prompt=params.prompt,
        )

    def _enrich_system(self, params: AskLlmParams) -> str:
        """如果传入了 context_submission_id，自动补全提交代码与判题结果到 system prompt。"""
        if params.context_submission_id is None:
            return params.system_setting
        submission = self._submission_repository.get_by_id(params.context_submission_id)
        if submission is None:
            return params.system_setting
        code_snippet = submission.code_content or "(无代码)"
        context_block = (
            f"\n\n[参考提交 #{submission.id}] "
            f"用户: {submission.user_id} | "
            f"语言: {submission.language} | "
            f"判题结果: {submission.status} | "
            f"代码:\n```\n{code_snippet}\n```"
        )
        return params.system_setting + context_block

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("仅教师可使用 LLM 功能")

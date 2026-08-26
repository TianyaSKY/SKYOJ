"""同步 LLM 对话业务服务。"""

from app.clients.llm_client import LlmClient
from app.domain.errors import ExternalServiceError, LlmConfigError
from app.domain.llm import AskLlmParams


class LlmFacadeService:
    """编排同步 LLM 对话；耗时脚本任务由 Judge Worker 执行。"""

    def __init__(self, llm_client: LlmClient) -> None:
        self._llm_client = llm_client

    def ask(self, params: AskLlmParams) -> dict:
        """调用配置好的 LLM 客户端。"""
        if not self._llm_client.is_configured():
            raise LlmConfigError("LLM 环境变量未完整配置")
        try:
            final_system = self._enrich_system(params)
            return self._llm_client.chat_json(
                system_setting=final_system,
                prompt=params.prompt,
                output_format=params.output_format,
            )
        except RuntimeError as exc:
            raise ExternalServiceError(str(exc)) from exc

    def ask_stream(self, params: AskLlmParams):
        """SSE 流式调用 LLM，返回生成器。"""
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
        from app.repositories.submission_repository import SubmissionRepository
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            repo = SubmissionRepository(db)
            submission = repo.get_by_id(params.context_submission_id)
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
        finally:
            db.close()


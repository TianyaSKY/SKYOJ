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
            return self._llm_client.chat_json(
                system_setting=params.system_setting,
                prompt=params.prompt,
                output_format=params.output_format,
            )
        except RuntimeError as exc:
            raise ExternalServiceError(str(exc)) from exc

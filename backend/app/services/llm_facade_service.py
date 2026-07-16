"""同步 LLM 与测例生成功能的业务服务。"""

from app.clients.llm_client import LlmClient
from app.domain.errors import ExternalServiceError, LlmConfigError
from app.domain.llm import AskLlmParams, ExecuteTestGenerationParams


class LlmFacadeService:
    """编排同步 LLM 对话与测例脚本生成。"""

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

    def execute_test_generation(self, params: ExecuteTestGenerationParams) -> str:
        """调用既有测例生成实现，并统一返回业务错误。"""
        if params.problem_type and params.problem_type != "acm":
            from app.services.judge_service import save_non_acm_script
            success, message = save_non_acm_script(
                params.problem_id, params.code, params.problem_type, params.language
            )
        else:
            from app.services.test_gen_service import run_test_generation
            success, message = run_test_generation(params.problem_id, params.code)
        if not success:
            raise ExternalServiceError(message)
        return message

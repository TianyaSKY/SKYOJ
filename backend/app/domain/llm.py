"""同步 LLM 功能的业务参数。"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class AskLlmParams:
    """请求 LLM 对话的参数。"""

    system_setting: str
    prompt: str
    output_format: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class ExecuteTestGenerationParams:
    """执行测试数据生成的参数。"""

    problem_id: int
    code: str
    problem_type: Optional[str]
    language: str

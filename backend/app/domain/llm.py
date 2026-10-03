"""同步 LLM 功能的业务参数。"""

from dataclasses import dataclass
from typing import Optional

from app.domain.json import JsonValue


@dataclass(frozen=True)
class AskLlmParams:
    """请求 LLM 对话的参数。"""

    system_setting: str
    prompt: str
    requester_role: str
    output_format: Optional[dict[str, JsonValue]] = None
    # 若提供，AI 答疑时自动带入该提交代码与判题结果作为上下文。
    context_submission_id: Optional[int] = None

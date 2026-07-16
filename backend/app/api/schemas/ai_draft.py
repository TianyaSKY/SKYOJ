"""AI 草稿箱 API 请求体模型。"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class GenerateProblemDraftBody(BaseModel):
    """提交 AI 出题异步任务。"""

    background: str = Field(min_length=1, max_length=5000)
    difficulty: str = Field(default="简单", max_length=32)


class GenerateTestScriptDraftBody(BaseModel):
    """提交测例脚本生成异步任务。"""

    problem_id: int = Field(ge=1)
    direction: str = Field(default="", max_length=5000)


class ExecuteTestDataDraftBody(BaseModel):
    """提交测例执行异步任务。"""

    problem_id: int = Field(ge=1)
    code: str = Field(min_length=1)
    type: str = Field(default="acm", max_length=32)
    language: str = Field(default="python", max_length=32)
    source_draft_id: Optional[int] = Field(default=None, ge=1)


class AskLlmBody(BaseModel):
    """同步 LLM 对话请求。"""

    system_setting: str = Field(min_length=1, max_length=10000)
    prompt: str = Field(min_length=1, max_length=50000)
    output_format: Optional[dict[str, Any]] = None


class ExecuteTestGenerationBody(BaseModel):
    """同步执行测例生成请求。"""

    problem_id: int = Field(ge=1)
    code: str = Field(min_length=1)
    type: Optional[str] = Field(default=None, max_length=32)
    language: str = Field(default="python", min_length=1, max_length=32)

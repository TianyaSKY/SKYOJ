"""调试运行响应模型。"""

from datetime import datetime

from pydantic import BaseModel


class CreateDebugRunResponse(BaseModel):
    message: str
    debug_run_id: int
    status: str
    exam_id: int | None


class DebugRunResponse(BaseModel):
    id: int
    status: str
    language: str
    case_name: str | None
    input: str | None
    expected_output: str | None
    actual_output: str | None
    error_output: str | None
    time_used_ms: int | None
    memory_used_kb: int | None
    created_at: datetime | None
    finished_at: datetime | None
    problem_id: int
    exam_id: int | None

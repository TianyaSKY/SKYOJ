"""考试 API 请求体模型。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateExamBody(BaseModel):
    """创建考试请求体。"""

    title: str = Field(min_length=1, max_length=100)
    description: str = ""
    start_time: datetime
    end_time: datetime
    password: Optional[str] = None
    is_visible: bool = False


class UpdateExamBody(BaseModel):
    """更新考试请求体（所有字段可选）。"""

    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    password: Optional[str] = None
    is_visible: Optional[bool] = None


class EnterExamBody(BaseModel):
    """进入考试请求体。"""

    password: Optional[str] = None


class AddProblemToExamBody(BaseModel):
    """向考试添加题目请求体。"""

    problem_id: int = Field(ge=1)
    display_id: Optional[str] = None
    score: int = Field(default=100, ge=1)

"""查重 API 请求体与响应模型。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MatchedBlockResponse(BaseModel):
    start_a: int = Field(description="提交 A 匹配块起始行（1-indexed）")
    end_a: int = Field(description="提交 A 匹配块结束行")
    start_b: int = Field(description="提交 B 匹配块起始行")
    end_b: int = Field(description="提交 B 匹配块结束行")
    code_a: str = Field(description="提交 A 对应代码片段")
    code_b: str = Field(description="提交 B 对应代码片段")


class PlagiarismReportResponse(BaseModel):
    id: int
    submission_a_id: int
    submission_b_id: int
    username_a: str
    username_b: str
    similarity_score: float
    matched_blocks: list[MatchedBlockResponse]
    status: str
    created_at: Optional[datetime]


class PlagiarismScanResponse(BaseModel):
    job_id: int
    message: str


class PlagiarismListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    reports: list[PlagiarismReportResponse]

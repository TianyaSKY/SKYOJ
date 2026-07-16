"""搜索 API 请求体模型。"""

from pydantic import BaseModel, Field


class SearchBody(BaseModel):
    """搜索请求体。"""

    query: str = Field(min_length=1, max_length=255)
    mode: str = Field(default="semantic", pattern="^(normal|semantic)$")
    top_k: int = Field(default=5, ge=1, le=50)

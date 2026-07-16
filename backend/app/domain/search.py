"""搜索相关业务参数与结果。"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SearchParams:
    """搜索请求参数。"""

    query: str
    mode: str = "semantic"
    top_k: int = 5
    user_id: Optional[int] = None


@dataclass(frozen=True)
class SearchResultItem:
    """搜索结果单项。"""

    id: int
    title: str
    content: str
    type: str
    language: str
    time_limit: int
    memory_limit: int
    score: float = 0.0


@dataclass(frozen=True)
class SearchResults:
    """搜索结果集合。"""

    results: list[SearchResultItem]
    total: int

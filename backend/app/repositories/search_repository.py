"""搜索数据访问。"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.search_history import SearchHistory


class SearchRepository:
    """封装普通搜索及搜索历史持久化。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def search_problems(self, query: str, top_k: int):
        return self._db.query(Problem).filter(or_(Problem.title.like(f"%{query}%"), Problem.content.like(f"%{query}%"))).limit(top_k).all()

    def add_history(self, user_id: int, query: str) -> None:
        self._db.add(SearchHistory(user_id=user_id, query=query))
        self._db.commit()

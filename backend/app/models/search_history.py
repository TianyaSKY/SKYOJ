from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="search_history")

    def __repr__(self):
        return f"<SearchHistory {self.query} by User {self.user_id}>"

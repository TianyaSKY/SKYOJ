"""AI 异步任务草稿模型。"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class AiDraft(Base):
    """存储 AI 出题 / 测例生成等异步任务及其结果。"""

    __tablename__ = "ai_drafts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # problem_generation | test_script_generation | test_data_execution
    task_type = Column(String(64), nullable=False, index=True)
    # pending | running | success | failed
    status = Column(String(32), nullable=False, default="pending", index=True)

    title = Column(String(255), nullable=False, default="")
    # 关联题目（测例相关任务）
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)

    request_payload = Column(Text, nullable=True)
    result_payload = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # 出题草稿被应用到正式题目的时间
    consumed_at = Column(DateTime, nullable=True)

    user = relationship("User", lazy=True)
    problem = relationship("Problem", lazy=True)

    def __repr__(self) -> str:
        return f"<AiDraft {self.id} {self.task_type} {self.status}>"

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    """审计日志：记录写操作（POST/PUT/DELETE）和敏感读取。"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    method = Column(String(16), nullable=False)
    path = Column(String(255), nullable=False)
    status_code = Column(Integer)
    ip = Column(String(64))
    user_agent = Column(String(255))
    payload_summary = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} {self.method} {self.path} status={self.status_code}>"

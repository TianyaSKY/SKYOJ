from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    file_path = Column(String(256), nullable=False)
    file_size = Column(String(64))
    status = Column(String(32), nullable=False, default="ready", index=True)
    temp_path = Column(String(500), nullable=True)
    file_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User", back_populates="datasets")

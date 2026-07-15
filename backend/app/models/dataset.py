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
    uploader_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User", back_populates="datasets")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader": self.uploader.username if self.uploader else "Unknown",
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat(),
            "download_url": f"/api/datasets/{self.id}/download",
        }

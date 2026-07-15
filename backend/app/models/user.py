from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    # role: enum('student', 'teacher')
    role = Column(Enum("student", "teacher"), default="student")
    avatar = Column(String(255))  # 头像 URL 或文件名

    submissions = relationship("Submission", back_populates="user", lazy=True)
    datasets = relationship("Dataset", back_populates="uploader", lazy=True)
    created_exams = relationship("Exam", back_populates="creator", lazy=True)
    search_history = relationship("SearchHistory", back_populates="user", lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"

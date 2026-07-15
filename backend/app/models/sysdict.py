from sqlalchemy import Column, Integer, String

from app.database import Base


class SysDict(Base):
    __tablename__ = "sys_dict"

    id = Column(Integer, primary_key=True)
    key = Column(String(100))
    val = Column(String(100))

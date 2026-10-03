"""启动时检查连接、建表和初始化默认数据。"""

import time

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.defaults import sys_dict_kv
from app.persistence.database import Base, SessionLocal, engine
from app.persistence.system import SysDict


def init_db():
    """检查连接、创建缺失的表并初始化默认数据。"""
    retries = 5
    while retries > 0:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.success("数据库连接成功")
            Base.metadata.create_all(bind=engine)
            logger.success("数据库表初始化完成")

            db = SessionLocal()
            try:
                if db.query(SysDict).count() == 0:
                    for key, val in sys_dict_kv.items():
                        db.add(SysDict(key=key, val=str(val)))
                    db.commit()
                    logger.success("系统字典已根据默认配置完成初始化")
            finally:
                db.close()
            return
        except OperationalError as exc:
            retries -= 1
            logger.warning(
                "数据库暂不可用，准备重试，第 {} 次/共 5 次，原因：{}",
                5 - retries,
                exc,
            )
            time.sleep(3)
        except Exception as exc:
            retries -= 1
            logger.exception(
                "数据库初始化失败，准备重试，第 {} 次/共 5 次，原因：{}",
                5 - retries,
                exc,
            )
            time.sleep(3)
    raise RuntimeError("数据库初始化失败，请检查连接配置、建表权限及已有表结构")

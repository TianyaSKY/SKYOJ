"""启动时检查连接、迁移版本和初始化默认数据。"""

import time
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.defaults import sys_dict_kv
from app.persistence.database import SessionLocal, engine
from app.persistence.system import SysDict


def init_db() -> None:
    """检查连接及迁移版本，只初始化默认数据。"""
    retries = 5
    while retries > 0:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                config = Config(
                    str(Path(__file__).resolve().parents[2] / "alembic.ini")
                )
                expected = set(ScriptDirectory.from_config(config).get_heads())
                current = set(
                    MigrationContext.configure(connection).get_current_heads()
                )
                if current != expected:
                    raise RuntimeError(
                        "数据库迁移未完成，请先执行 alembic upgrade head；已有未版本化数据库需先校验并登记初始版本"
                    )
            logger.success("数据库连接成功")
            logger.success("数据库迁移版本检查通过")

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
        except RuntimeError:
            # 版本不匹配不是暂时性连接失败，直接拒绝启动。
            raise
        except Exception as exc:
            retries -= 1
            logger.exception(
                "数据库初始化失败，准备重试，第 {} 次/共 5 次，原因：{}",
                5 - retries,
                exc,
            )
            time.sleep(3)
    raise RuntimeError("数据库初始化失败，请检查连接配置、迁移版本及已有表结构")

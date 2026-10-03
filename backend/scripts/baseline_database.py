"""为已有完整数据库登记初始版本；先校验结构，不执行业务表 DDL。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.persistence.database import Base, engine
from loguru import logger
from sqlalchemy.engine import Connection


def baseline(connection: Connection) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    if ScriptDirectory.from_config(config).get_heads() != ["0001"]:
        raise RuntimeError(
            "初始版本接入脚本仅用于 0001，请使用对应版本的已审核迁移接入旧库"
        )
    context = MigrationContext.configure(connection, opts={"compare_type": True})
    revisions = context.get_current_heads()
    if revisions and revisions != ("0001",):
        raise RuntimeError("数据库已有其他迁移版本，请先检查版本历史")
    differences = compare_metadata(context, Base.metadata)
    if differences:
        # 只输出结构差异，不查询业务数据或记录连接凭据。
        logger.error("数据库与初始版本结构不一致 differences={}", differences)
        raise RuntimeError("结构校验失败，请备份并审核修复 SQL 后重试；未登记版本")
    config.attributes["connection"] = connection
    command.stamp(config, "0001")
    logger.success("数据库结构校验通过，已登记初始版本 0001")


if __name__ == "__main__":
    with engine.begin() as connection:
        baseline(connection)

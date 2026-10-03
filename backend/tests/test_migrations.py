"""初始迁移与已有库接入均在临时数据库验证。"""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from app.persistence.database import Base
from app.persistence.system import SysDict
from scripts.baseline_database import baseline
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import SQLAlchemyError

CONFIG = Path(__file__).parents[1] / "alembic.ini"


def upgrade(connection):
    config = Config(str(CONFIG))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


def test_empty_database_upgrade_repeat_and_metadata_parity():
    with create_engine("sqlite://").begin() as connection:
        upgrade(connection)
        assert set(inspect(connection).get_table_names()) == set(
            Base.metadata.tables
        ) | {"alembic_version"}
        assert not compare_metadata(
            MigrationContext.configure(connection), Base.metadata
        )
        connection.execute(SysDict.__table__.insert().values(key="保留", val="数据"))
        upgrade(connection)
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "0001"
        )
        assert connection.execute(text("SELECT val FROM sys_dict")).scalar() == "数据"


def test_existing_database_is_verified_before_stamp():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(SysDict.__table__.insert().values(key="保留", val="数据"))
        baseline(connection)
        baseline(connection)
        upgrade(connection)
        assert connection.execute(text("SELECT val FROM sys_dict")).scalar() == "数据"
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "0001"
        )


def test_mismatched_database_is_not_stamped():
    with create_engine("sqlite://").begin() as connection:
        connection.execute(
            text("CREATE TABLE sys_dict (id INTEGER PRIMARY KEY, obsolete TEXT)")
        )
        with pytest.raises(RuntimeError, match="结构校验失败"):
            baseline(connection)
        assert "alembic_version" not in inspect(connection).get_table_names()
        assert "obsolete" in {
            column["name"] for column in inspect(connection).get_columns("sys_dict")
        }


def test_migration_ddl_failure_is_not_silenced():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "before_cursor_execute")
    def reject_ddl(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("CREATE TABLE"):
            raise SQLAlchemyError("DDL rejected")

    with (
        engine.begin() as connection,
        pytest.raises(SQLAlchemyError, match="DDL rejected"),
    ):
        upgrade(connection)

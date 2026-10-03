"""迁移必须兼容空库、旧库和重复执行，并保留已有数据。"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

CONFIG = Path(__file__).parents[1] / "alembic.ini"


def upgrade(connection):
    config = Config(str(CONFIG))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


def test_empty_database_upgrade_and_repeat():
    from app.persistence.database import Base

    with create_engine("sqlite://").begin() as connection:
        upgrade(connection)
        tables = set(inspect(connection).get_table_names())
        assert set(Base.metadata.tables) <= tables
        upgrade(connection)
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "0001"
        )
        assert "case_results" in {
            c["name"] for c in inspect(connection).get_columns("submissions")
        }


def test_legacy_database_preserves_rows_and_adds_columns():
    with create_engine("sqlite://").begin() as connection:
        connection.execute(
            text("CREATE TABLE exams (id INTEGER PRIMARY KEY, title VARCHAR(100))")
        )
        connection.execute(text("INSERT INTO exams VALUES (1, '已有考试')"))
        connection.execute(
            text("CREATE TABLE datasets (id INTEGER PRIMARY KEY, name VARCHAR(128))")
        )
        connection.execute(text("INSERT INTO datasets VALUES (1, '已有数据集')"))
        connection.execute(
            text(
                "CREATE TABLE submissions (id INTEGER PRIMARY KEY, exam_id INTEGER, problem_id INTEGER, user_id INTEGER, created_at DATETIME)"
            )
        )
        upgrade(connection)
        assert connection.execute(
            text("SELECT title, contest_type FROM exams")
        ).one() == ("已有考试", "icpc")
        assert connection.execute(text("SELECT name, status FROM datasets")).one() == (
            "已有数据集",
            "ready",
        )
        assert "case_results" in {
            c["name"] for c in inspect(connection).get_columns("submissions")
        }
        upgrade(connection)


def test_migration_ddl_failure_is_not_silenced():
    from sqlalchemy import event

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

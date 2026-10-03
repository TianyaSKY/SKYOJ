"""启动建表可重复执行、保留已有数据，建表失败时拒绝启动。"""

import pytest
from app.persistence import bootstrap
from app.persistence.database import Base
from app.persistence.system import SysDict
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def startup_engine(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(bootstrap, "engine", engine)
    monkeypatch.setattr(bootstrap, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(bootstrap.time, "sleep", lambda _: None)
    yield engine
    engine.dispose()


def test_startup_creates_tables_and_preserves_existing_data(startup_engine):
    bootstrap.init_db()
    assert set(inspect(startup_engine).get_table_names()) == set(Base.metadata.tables)
    sessions = sessionmaker(bind=startup_engine)
    with sessions.begin() as db:
        assert db.scalar(select(SysDict.id).limit(1)) is not None
        db.add(SysDict(key="startup_test", val="保留数据"))
    bootstrap.init_db()
    with sessions() as db:
        assert (
            db.scalar(select(SysDict.val).where(SysDict.key == "startup_test"))
            == "保留数据"
        )


def test_startup_rejects_failed_table_creation(startup_engine):
    @event.listens_for(startup_engine, "before_cursor_execute")
    def reject_ddl(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("CREATE TABLE"):
            raise SQLAlchemyError("DDL rejected")

    with pytest.raises(RuntimeError, match="数据库初始化失败"):
        bootstrap.init_db()

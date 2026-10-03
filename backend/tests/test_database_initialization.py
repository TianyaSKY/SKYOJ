"""启动建表可重复执行、保留已有数据，建表失败时拒绝启动。"""

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app import main
from app.persistence.database import Base
from app.persistence.system import SysDict


@pytest.fixture
def startup_engine(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(main.time, "sleep", lambda _: None)
    yield engine
    engine.dispose()


def test_startup_creates_tables_and_preserves_existing_data(startup_engine):
    main.init_db()
    assert set(inspect(startup_engine).get_table_names()) == set(Base.metadata.tables)
    sessions = sessionmaker(bind=startup_engine)
    with sessions.begin() as db:
        assert db.scalar(select(SysDict.id).limit(1)) is not None
        db.add(SysDict(key="startup_test", val="保留数据"))
    main.init_db()
    with sessions() as db:
        assert db.scalar(select(SysDict.val).where(SysDict.key == "startup_test")) == "保留数据"


def test_startup_rejects_failed_table_creation(startup_engine):
    @event.listens_for(startup_engine, "before_cursor_execute")
    def reject_ddl(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("CREATE TABLE"):
            raise SQLAlchemyError("DDL rejected")

    with pytest.raises(RuntimeError, match="数据库初始化失败"):
        main.init_db()

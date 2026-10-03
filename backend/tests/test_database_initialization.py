"""应用启动只检查迁移版本并初始化种子，不执行业务表 DDL。"""

import pytest
from app.persistence import bootstrap
from app.persistence.system import SysDict
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker
from test_migrations import upgrade


@pytest.fixture
def startup_engine(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(bootstrap, "engine", engine)
    monkeypatch.setattr(bootstrap, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(bootstrap.time, "sleep", lambda _: None)
    yield engine
    engine.dispose()


def test_startup_seeds_without_ddl_and_preserves_existing_data(startup_engine):
    with startup_engine.begin() as connection:
        upgrade(connection)

    @event.listens_for(startup_engine, "before_cursor_execute")
    def reject_ddl(conn, cursor, statement, parameters, context, executemany):
        assert not statement.lstrip().upper().startswith(("CREATE ", "ALTER ", "DROP "))

    bootstrap.init_db()
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


def test_startup_rejects_unmigrated_database(startup_engine):
    with pytest.raises(RuntimeError, match="数据库迁移未完成"):
        bootstrap.init_db()


def test_startup_rejects_wrong_revision(startup_engine):
    with startup_engine.begin() as connection:
        upgrade(connection)
        connection.execute(text("UPDATE alembic_version SET version_num = 'unknown'"))
    with pytest.raises(RuntimeError, match="数据库迁移未完成"):
        bootstrap.init_db()

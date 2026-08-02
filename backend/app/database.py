from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


# pool_pre_ping avoids stale MySQL connections after idle
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    # Import models so metadata is populated
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_dataset_columns()


def _ensure_dataset_columns() -> None:
    """为没有迁移框架的旧数据库补齐文件任务字段。"""
    inspector = inspect(engine)
    existing_columns = {
        column["name"] for column in inspector.get_columns("datasets")
    }
    required_columns = {
        "status": "VARCHAR(32) NOT NULL DEFAULT 'ready'",
        "temp_path": "VARCHAR(500) NULL",
        "file_hash": "VARCHAR(64) NULL",
        "error_message": "TEXT NULL",
    }
    missing_columns = [
        (name, definition)
        for name, definition in required_columns.items()
        if name not in existing_columns
    ]
    if not missing_columns:
        return

    with engine.begin() as connection:
        for name, definition in missing_columns:
            connection.execute(
                text(f"ALTER TABLE datasets ADD COLUMN {name} {definition}")
            )

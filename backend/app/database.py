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
    _ensure_indexes()


def _ensure_indexes() -> None:
    """为没有迁移框架的旧数据库补齐查询索引。"""
    inspector = inspect(engine)
    required_indexes = {
        "submissions": {
            "ix_submissions_exam_problem_user": (
                "CREATE INDEX ix_submissions_exam_problem_user "
                "ON submissions (exam_id, problem_id, user_id)"
            ),
            "ix_submissions_created_at": (
                "CREATE INDEX ix_submissions_created_at ON submissions (created_at)"
            ),
        },
        "exam_problems": {
            "ix_exam_problems_exam_id": (
                "CREATE INDEX ix_exam_problems_exam_id ON exam_problems (exam_id)"
            ),
        },
    }
    missing = []
    for table, indexes in required_indexes.items():
        if table not in inspector.get_table_names():
            continue
        existing = {index["name"] for index in inspector.get_indexes(table)}
        for name, ddl in indexes.items():
            if name not in existing:
                missing.append(ddl)
    if not missing:
        return

    with engine.begin() as connection:
        for ddl in missing:
            connection.execute(text(ddl))


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

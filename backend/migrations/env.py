"""独立迁移入口，应用启动阶段不执行 DDL。"""

from alembic import context
from app import persistence  # noqa: F401
from app.persistence.database import Base, engine


def run_migrations() -> None:
    supplied = context.config.attributes.get("connection")
    if supplied is not None:
        context.configure(connection=supplied, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()

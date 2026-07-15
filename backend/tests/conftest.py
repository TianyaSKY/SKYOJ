"""Pytest fixtures — use isolated SQLite DB and the shipped FastAPI app."""

import os
import sys
from pathlib import Path

# Ensure backend root is on path and force test DB before app import
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB = BACKEND_ROOT / "test_skyoj.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENABLE_PLAGIARISM"] = "0"
os.environ["ENABLE_SEMANTIC_SEARCH"] = "0"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import after env is set so engine binds to SQLite
from app.database import Base, get_db
from app.main import create_app
import app.models  # noqa: F401 — register metadata


@pytest.fixture()
def client():
    engine = create_engine(
        f"sqlite:///{TEST_DB.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    application = create_app()

    # Skip heavy MySQL retry startup; tables already created above
    application.router.on_startup.clear()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = override_get_db

    with TestClient(application) as c:
        yield c

    application.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

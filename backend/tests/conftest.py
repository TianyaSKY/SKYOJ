"""pytest 全局 fixtures：测试数据库、客户端、认证 token。"""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def engine():
    """SQLite 内存引擎，所有测试共享同一 schema。"""
    from app.persistence.database import Base

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db_session(engine):
    """每个测试独立事务，测试结束自动回滚。"""
    from sqlalchemy.orm import Session

    connection = engine.connect()
    transaction = connection.begin()
    # SQLite 的 BEGIN 默认延迟到写入；显式开启外层事务，保证保存点释放不泄漏数据。
    connection.exec_driver_sql("BEGIN")
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session, monkeypatch):
    """带内存数据库的 TestClient，mock Docker 调用。"""
    import app.persistence.database

    monkeypatch.setattr(app.persistence.database, "SessionLocal", lambda: db_session)

    from unittest.mock import MagicMock, patch

    with patch("app.judging.sandbox.client") as mock_client:
        mock_container = MagicMock()
        mock_container.id = "test-container-123"
        mock_container.attrs = {}
        mock_client.containers.run.return_value = mock_container
        mock_container.exec_run.return_value = (0, "output")
        mock_container.logs.return_value = b""
        mock_container.wait.return_value = None

        from app.main import app

        yield TestClient(app)
        app.dependency_overrides.clear()


@pytest.fixture
def teacher_user(db_session):
    """创建一个教师用户并返回其 ORM 对象。"""
    import bcrypt
    from app.persistence.user import User

    user = User(
        username="test_teacher",
        password_hash=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode(),
        role="teacher",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_user(db_session):
    """创建一个学生用户并返回其 ORM 对象。"""
    import bcrypt
    from app.persistence.user import User

    user = User(
        username="test_student",
        password_hash=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode(),
        role="student",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def teacher_token(client, teacher_user):
    """返回教师 JWT token。"""
    resp = client.post(
        "/api/auth/login", json={"username": "test_teacher", "password": "password123"}
    )
    assert resp.status_code == 200
    return resp.json()["token"]


@pytest.fixture
def student_token(client, student_user):
    """返回学生 JWT token。"""
    resp = client.post(
        "/api/auth/login", json={"username": "test_student", "password": "password123"}
    )
    assert resp.status_code == 200
    return resp.json()["token"]


@pytest.fixture
def sample_problem(db_session):
    """创建一个 ACM 题目用于测试。"""
    from app.persistence.problem import Problem

    problem = Problem(
        title="两数之和",
        content="给定一个整数数组 nums 和目标值 target，返回两个数的下标。",
        type="acm",
        language="python",
        time_limit=1000,
        memory_limit=128,
    )
    db_session.add(problem)
    db_session.commit()
    db_session.refresh(problem)
    return problem

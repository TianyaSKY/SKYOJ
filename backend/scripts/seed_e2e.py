"""为临时 SQLite E2E 数据库生成固定账号和样例，拒绝写入已有业务数据。"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from app.core.defaults import sys_dict_kv
from app.core.passwords import hash_password
from app.persistence import Exam, ExamProblem, Problem, Submission, SysDict, User
from app.persistence.database import SessionLocal, engine
from loguru import logger
from sqlalchemy import select


def seed() -> None:
    if (
        engine.url.get_backend_name() != "sqlite"
        or Path(engine.url.database or "").name != "skyoj-e2e.sqlite"
    ):
        raise RuntimeError("E2E 初始化只允许写入专用 skyoj-e2e.sqlite 数据库")
    command.upgrade(
        Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head"
    )
    with SessionLocal.begin() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            raise RuntimeError("E2E 数据库已有用户，请使用新的临时数据库")
        db.add_all(
            [
                User(
                    id=1,
                    username="test_student",
                    password_hash=hash_password("Test123456"),
                    role="student",
                ),
                User(
                    id=2,
                    username="test_teacher",
                    password_hash=hash_password("Test123456"),
                    role="teacher",
                ),
            ]
        )
        db.add_all(
            SysDict(key=key, val=str(value)) for key, value in sys_dict_kv.items()
        )
        for problem_id, title in [
            (1000, "A+B Problem"),
            (1001, "Prime Number"),
            (1002, "Binary Search"),
        ]:
            db.add(
                Problem(
                    id=problem_id,
                    title=title,
                    content="# 样例题目\n输入两个整数，输出它们的和。",
                    type="acm",
                    language="python",
                    template_code="print(sum(map(int, input().split())))",
                )
            )
        now = datetime.now(UTC).replace(tzinfo=None)
        db.add_all(
            [
                Exam(
                    id=1,
                    title="Weekly Contest 1",
                    description="E2E 正在进行的比赛",
                    start_time=now - timedelta(days=1),
                    end_time=now + timedelta(days=1),
                    password="contest123",
                    is_visible=True,
                    created_by=2,
                ),
                Exam(
                    id=2,
                    title="Mid-term Exam",
                    description="E2E 已结束的比赛",
                    start_time=now - timedelta(days=3),
                    end_time=now - timedelta(days=2),
                    password="exam456",
                    is_visible=True,
                    created_by=2,
                ),
            ]
        )
        db.flush()
        db.add(ExamProblem(exam_id=1, problem_id=1000, display_id="A", score=100))
        db.add(
            Submission(
                id=1,
                user_id=1,
                problem_id=1000,
                language="python",
                code_content="print(3)",
                status="Accepted",
                score=100,
                created_at=now,
            )
        )
    logger.info("E2E 临时数据库样例初始化完成")


if __name__ == "__main__":
    seed()

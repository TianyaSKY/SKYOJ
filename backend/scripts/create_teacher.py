"""通过命令行创建教师账号。"""

from getpass import getpass
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.passwords import hash_password  # noqa: E402


def main() -> None:
    """读取凭据并创建教师账号。"""

    username = input("请输入教师用户名：").strip()
    if not username:
        raise SystemExit("用户名不能为空")
    if len(username) > 80:
        raise SystemExit("用户名不能超过 80 个字符")

    password = getpass("请输入密码：")
    confirm_password = getpass("请再次输入密码：")

    if password != confirm_password:
        raise SystemExit("两次输入的密码不一致")
    if len(password) < 8:
        raise SystemExit("教师密码至少需要 8 位")
    if len(password) > 128:
        raise SystemExit("密码不能超过 128 个字符")

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing is not None:
            raise SystemExit("该用户名已经存在")

        user = User(
            username=username,
            password_hash=hash_password(password),
            role="teacher",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"教师账号创建成功，用户 ID：{user.id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

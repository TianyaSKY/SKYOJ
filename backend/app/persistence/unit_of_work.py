"""业务服务显式控制事务；仓储只负责 flush。"""

from collections.abc import Iterator
from contextlib import contextmanager
from sqlalchemy.orm import Session


class UnitOfWork:
    def __init__(self, db: Session) -> None:
        self._db = db

    def commit(self) -> None:
        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def rollback(self) -> None:
        self._db.rollback()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """多个仓储写操作作为一个业务事务提交，任意步骤失败即回滚。"""
        try:
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise

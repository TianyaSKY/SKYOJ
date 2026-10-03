"""文件删除补偿：先同盘改名暂存，事务失败恢复，提交成功再清理。"""

import shutil
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from loguru import logger


@contextmanager
def stage_file_deletion(paths: list[Path]) -> Iterator[None]:
    """保留原文件直至调用方成功提交；清理失败保留暂存文件并记录位置。"""
    staged: list[tuple[Path, Path]] = []
    try:
        for original in dict.fromkeys(paths):
            if not original.exists() and not original.is_symlink():
                continue
            trash = original.parent / ".trash"
            trash.mkdir(exist_ok=True)
            temporary = trash / f"{uuid.uuid4().hex}-{original.name}"
            original.rename(temporary)
            staged.append((original, temporary))
            logger.info("删除文件暂存 original={} temporary={}", original, temporary)
        yield
    except Exception:
        restore_error: OSError | None = None
        for original, temporary in reversed(staged):
            try:
                if original.exists() or original.is_symlink():
                    raise FileExistsError(f"恢复目标已存在：{original}")
                temporary.rename(original)
                logger.info("删除失败，已恢复文件 original={}", original)
            except OSError as exc:
                logger.exception(
                    "文件恢复失败 original={} temporary={}", original, temporary
                )
                restore_error = exc
        if restore_error is not None:
            raise restore_error
        raise
    else:
        for original, temporary in staged:
            try:
                if temporary.is_symlink() or not temporary.is_dir():
                    temporary.unlink()
                else:
                    shutil.rmtree(temporary)
                logger.info("删除文件完成 original={}", original)
            except OSError:
                # 数据库已提交，不能再恢复文件或将业务删除报告为失败。
                logger.exception(
                    "数据库删除已提交，暂存文件待清理 temporary={}", temporary
                )

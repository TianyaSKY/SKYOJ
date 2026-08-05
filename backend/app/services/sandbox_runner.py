"""沙箱容器运行器：统一封装判题/生成沙箱容器的生命周期与文件传输。

本模块不依赖任何 service 模块，供判题模式（acm/oop/kaggle）与测例生成服务复用。
"""

import io
import os
import tarfile

from loguru import logger

IMAGE_NAME = "skyoj-runner"
_client = None


def _get_docker_client():
    global _client
    if _client is None:
        import docker

        _client = docker.from_env()
    return _client


class _ClientProxy:
    """向后兼容代理：首次访问属性时惰性初始化 docker 客户端。"""

    def __getattr__(self, name):
        return getattr(_get_docker_client(), name)


client = _ClientProxy()


def create_tar_stream(filename, content):
    """创建一个包含单个文件的 tar 流，用于上传到容器。"""
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        if isinstance(content, str):
            content = content.encode("utf-8")
        info = tarfile.TarInfo(name=filename)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    tar_stream.seek(0)
    return tar_stream


def create_tar_from_path(local_path, remote_filename):
    """
    将宿主机的本地文件打包成 tar 流
    :param local_path: 宿主机上的文件绝对路径
    :param remote_filename: 放入容器后的文件名
    """
    tar_stream = io.BytesIO()

    if not os.path.exists(local_path):
        raise FileNotFoundError(f"无法打包，找不到源文件: {local_path}")

    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tar.add(local_path, arcname=remote_filename)

    tar_stream.seek(0)
    return tar_stream


class SandboxRunner:
    """管理单个沙箱容器的生命周期：启动、传文件、执行命令、停止。"""

    def __init__(self, image: str = IMAGE_NAME) -> None:
        self._image = image
        self._container = None

    def launch(
        self,
        *,
        pids_limit=None,
        mem_limit=None,
        nano_cpus=None,
        network_mode: str = "none",
        workdir=None,
    ) -> None:
        """启动一个常驻沙箱容器（sleep 600），直至 stop() 才退出。"""
        kwargs = {}
        if pids_limit is not None:
            kwargs["pids_limit"] = pids_limit
        if mem_limit is not None:
            kwargs["mem_limit"] = mem_limit
        if nano_cpus is not None:
            kwargs["nano_cpus"] = nano_cpus
        if workdir is not None:
            # docker SDK 的 create_container/run 使用 working_dir（exec_run 才用 workdir）
            kwargs["working_dir"] = workdir
        self._container = client.containers.run(
            self._image,
            ["sleep", "600"],
            detach=True,
            remove=True,
            network_mode=network_mode,
            **kwargs,
        )

    def put_file(self, name: str, content) -> None:
        """将一段内容以指定文件名上传到容器 /app。"""
        self._container.put_archive("/app", create_tar_stream(name, content))

    def put_file_from_path(self, local_path: str, remote_name: str) -> None:
        """将宿主机上的文件打包上传到容器 /app。"""
        self._container.put_archive(
            "/app", create_tar_from_path(local_path, remote_name)
        )

    def exec_run(self, cmd: str, *, timeout=None, workdir=None) -> tuple[int, str]:
        """在容器中执行命令，返回 (exit_code, 输出文本)。"""
        kwargs = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        if workdir is not None:
            kwargs["workdir"] = workdir
        result = self._container.exec_run(cmd, **kwargs)
        output = result.output
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return result.exit_code, str(output)

    def get_archive(self, path: str):
        """从容器中取出目录/文件的 tar 流（透传 Docker SDK 返回值）。"""
        return self._container.get_archive(path)

    @staticmethod
    def is_tle(exit_code: int) -> bool:
        """shell timeout 命令的退出码 124 表示超时。"""
        return exit_code == 124

    def stop(self) -> None:
        """幂等停止并移除容器；未启动或已停止时直接返回。"""
        container = self._container
        if container is None:
            return
        self._container = None
        try:
            container.stop()
        except Exception as exc:
            logger.warning("停止沙箱容器失败: {}", exc)
        try:
            container.remove(force=True)
        except Exception:
            pass

    def __enter__(self) -> "SandboxRunner":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()

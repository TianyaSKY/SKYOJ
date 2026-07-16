"""数据集文件后台写入任务。"""

from threading import Thread

from app.clients.dataset_storage_client import DatasetStorageClient


class DatasetFileTask:
    """提交数据集文件写入任务。"""

    def __init__(self, storage_client: DatasetStorageClient) -> None:
        self._storage_client = storage_client

    def submit_save(self, content: bytes, file_path: str, dataset_id: int) -> None:
        """异步写入上传文件。"""
        Thread(
            target=self._storage_client.save,
            args=(file_path, content, dataset_id),
            daemon=True,
        ).start()

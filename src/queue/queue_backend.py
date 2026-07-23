"""抽象队列接口 — 支持内存队列 / Redis 切换"""

from abc import ABC, abstractmethod
from typing import Optional


class QueueBackend(ABC):
    """队列后端抽象接口"""

    @abstractmethod
    def push(self, task: dict) -> str:
        """推送任务到队列，返回 task_id"""
        ...

    @abstractmethod
    def pop(self) -> Optional[dict]:
        """从队列取出一个任务"""
        ...

    @abstractmethod
    def ack(self, task_id: str):
        """确认任务完成"""
        ...

    @abstractmethod
    def nack(self, task_id: str):
        """任务失败，重新入队"""
        ...

    @abstractmethod
    def size(self) -> int:
        """当前队列长度"""
        ...


class MemoryQueue(QueueBackend):
    """内存队列（默认）"""

    def __init__(self):
        self._queue = []
        self._in_progress = {}

    def push(self, task: dict) -> str:
        import uuid
        task_id = str(uuid.uuid4())[:8]
        task["task_id"] = task_id
        self._queue.append(task)
        return task_id

    def pop(self) -> Optional[dict]:
        if not self._queue:
            return None
        task = self._queue.pop(0)
        self._in_progress[task["task_id"]] = task
        return task

    def ack(self, task_id: str):
        self._in_progress.pop(task_id, None)

    def nack(self, task_id: str):
        task = self._in_progress.pop(task_id, None)
        if task:
            self._queue.append(task)

    def size(self) -> int:
        return len(self._queue)


class RedisQueue(QueueBackend):
    """Redis 队列（可选）"""

    def __init__(self, host="127.0.0.1", port=6379, db=0, password=""):
        self._available = False
        # TODO: redis.Redis(host=host, port=port, db=db, password=password)

    def push(self, task: dict) -> str:
        # TODO: redis.lpush(...)
        return ""

    def pop(self) -> Optional[dict]:
        # TODO: redis.brpop(...)
        return None

    def ack(self, task_id: str):
        pass

    def nack(self, task_id: str):
        pass

    def size(self) -> int:
        return 0


def create_queue_backend(config: dict) -> QueueBackend:
    """工厂方法：根据配置创建队列后端"""
    redis_cfg = config.get("redis", {})
    if redis_cfg.get("queue_enabled", False):
        return RedisQueue(
            host=redis_cfg.get("host", "127.0.0.1"),
            port=redis_cfg.get("port", 6379),
        )
    return MemoryQueue()

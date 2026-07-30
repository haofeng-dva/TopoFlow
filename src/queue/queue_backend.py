"""抽象队列接口，支持线程安全内存队列和 Redis。"""

import json
import threading
import uuid
from abc import ABC, abstractmethod
from collections import deque
from typing import Optional


class QueueBackend(ABC):
    @abstractmethod
    def push(self, task: dict) -> str: ...

    @abstractmethod
    def pop(self) -> Optional[dict]: ...

    @abstractmethod
    def ack(self, task_id: str): ...

    @abstractmethod
    def nack(self, task_id: str): ...

    @abstractmethod
    def size(self) -> int: ...


class MemoryQueue(QueueBackend):
    def __init__(self):
        self._queue = deque()
        self._in_progress = {}
        self._lock = threading.Lock()

    def push(self, task: dict) -> str:
        task_id = task.get("task_id") or uuid.uuid4().hex
        payload = {**task, "task_id": task_id}
        with self._lock:
            self._queue.append(payload)
        return task_id

    def pop(self) -> Optional[dict]:
        with self._lock:
            if not self._queue:
                return None
            task = self._queue.popleft()
            self._in_progress[task["task_id"]] = task
            return dict(task)

    def ack(self, task_id: str):
        with self._lock:
            self._in_progress.pop(task_id, None)

    def nack(self, task_id: str):
        with self._lock:
            task = self._in_progress.pop(task_id, None)
            if task:
                self._queue.appendleft(task)

    def size(self) -> int:
        with self._lock:
            return len(self._queue)


class RedisQueue(QueueBackend):
    def __init__(
        self,
        host="127.0.0.1",
        port=6379,
        db=0,
        password="",
        queue_name="topoflow:tasks",
        client=None,
    ):
        if client is None:
            try:
                import redis
            except ImportError as exc:
                raise RuntimeError("Redis 队列需要安装 redis 包") from exc
            client = redis.Redis(
                host=host, port=port, db=db, password=password or None, decode_responses=True
            )
        self.client = client
        self.queue_name = queue_name
        self.processing_name = f"{queue_name}:processing"
        try:
            self.client.ping()
        except Exception as exc:
            raise RuntimeError(f"无法连接 Redis: {host}:{port}/{db}") from exc

    def push(self, task: dict) -> str:
        task_id = task.get("task_id") or uuid.uuid4().hex
        payload = {**task, "task_id": task_id}
        self.client.rpush(self.queue_name, json.dumps(payload, ensure_ascii=False))
        return task_id

    def pop(self) -> Optional[dict]:
        encoded = self.client.lpop(self.queue_name)
        if encoded is None:
            return None
        task = json.loads(encoded)
        self.client.hset(self.processing_name, task["task_id"], encoded)
        return task

    def ack(self, task_id: str):
        self.client.hdel(self.processing_name, task_id)

    def nack(self, task_id: str):
        pipeline = self.client.pipeline(transaction=True)
        encoded = self.client.hget(self.processing_name, task_id)
        if encoded is not None:
            pipeline.hdel(self.processing_name, task_id)
            pipeline.lpush(self.queue_name, encoded)
            pipeline.execute()

    def size(self) -> int:
        return int(self.client.llen(self.queue_name))


def create_queue_backend(config: dict) -> QueueBackend:
    redis_cfg = config.get("redis", {})
    if redis_cfg.get("queue_enabled", False):
        return RedisQueue(
            host=redis_cfg.get("host", "127.0.0.1"),
            port=redis_cfg.get("port", 6379),
            db=redis_cfg.get("db", 0),
            password=redis_cfg.get("password", ""),
        )
    return MemoryQueue()

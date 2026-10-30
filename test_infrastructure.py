"""缓存、持久状态、队列和工具发现测试。"""

import shutil
import unittest
import uuid
from pathlib import Path

from src.api.server import TaskStore
from src.cache.file_cache import FileCache, cache_key
from src.queue.queue_backend import MemoryQueue, RedisQueue
from src.tools.blender import find_blender


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.operations = []

    def hdel(self, name, key):
        self.operations.append(("hdel", name, key))
        return self

    def lpush(self, name, value):
        self.operations.append(("lpush", name, value))
        return self

    def execute(self):
        for operation in self.operations:
            getattr(self.client, operation[0])(*operation[1:])


class FakeRedis:
    def __init__(self):
        self.lists = {}
        self.hashes = {}

    def ping(self): return True
    def rpush(self, name, value): self.lists.setdefault(name, []).append(value)
    def lpush(self, name, value): self.lists.setdefault(name, []).insert(0, value)
    def lpop(self, name):
        values = self.lists.setdefault(name, [])
        return values.pop(0) if values else None
    def llen(self, name): return len(self.lists.setdefault(name, []))
    def hset(self, name, key, value): self.hashes.setdefault(name, {})[key] = value
    def hget(self, name, key): return self.hashes.setdefault(name, {}).get(key)
    def hdel(self, name, key): self.hashes.setdefault(name, {}).pop(key, None)
    def pipeline(self, transaction=True): return FakePipeline(self)


class InfrastructureTests(unittest.TestCase):
    def temporary_directory(self, name):
        path = Path(__file__).parent / ".test-tmp" / f"{name}-{uuid.uuid4().hex}"
        path.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def test_file_cache_roundtrip_and_key_changes_with_content(self):
        root = self.temporary_directory("cache")
        source = root / "source.obj"
        source.write_text("v 0 0 0\n", encoding="utf-8")
        first_key = cache_key("diagnosis", str(source), {"preset": "ue5"})
        cache = FileCache(str(root / "entries"), max_entries=2)
        cache.set("diagnosis", first_key, {"value": 1})
        self.assertEqual(cache.get("diagnosis", first_key)["value"], 1)
        source.write_text("v 1 0 0\n", encoding="utf-8")
        self.assertNotEqual(first_key, cache_key("diagnosis", str(source), {"preset": "ue5"}))

    def test_sqlite_task_store_survives_reopen(self):
        root = self.temporary_directory("task-store")
        database = root / "tasks.sqlite3"
        first = TaskStore(str(database))
        first.create("task-1", {"filename": "hero.obj"})
        first.update("task-1", status="running")
        first.close()
        second = TaskStore(str(database))
        self.addCleanup(second.close)
        self.assertEqual(second.get("task-1")["status"], "running")

    def test_sqlite_task_store_recovers_incomplete_tasks(self):
        root = self.temporary_directory("task-recovery")
        store = TaskStore(str(root / "tasks.sqlite3"))
        self.addCleanup(store.close)
        store.create("task-1", {"filename": "hero.obj"})
        store.update("task-1", status="running")
        self.assertEqual(store.recover_incomplete(), 1)
        self.assertEqual(store.get("task-1")["status"], "interrupted")

    def test_memory_queue_ack_and_nack(self):
        queue = MemoryQueue()
        task_id = queue.push({"kind": "run"})
        task = queue.pop()
        self.assertEqual(task["task_id"], task_id)
        queue.nack(task_id)
        self.assertEqual(queue.size(), 1)
        queue.ack(queue.pop()["task_id"])
        self.assertEqual(queue.size(), 0)

    def test_redis_queue_protocol_with_fake_client(self):
        queue = RedisQueue(client=FakeRedis())
        task_id = queue.push({"kind": "run"})
        self.assertEqual(queue.size(), 1)
        self.assertEqual(queue.pop()["task_id"], task_id)
        queue.nack(task_id)
        self.assertEqual(queue.size(), 1)
        queue.ack(queue.pop()["task_id"])
        self.assertEqual(queue.size(), 0)

    @unittest.skipUnless(find_blender(), "Blender 未安装（CI 环境跳过）")
    def test_blender_is_discoverable(self):
        self.assertTrue(find_blender())


if __name__ == "__main__":
    unittest.main()

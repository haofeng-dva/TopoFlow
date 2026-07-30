import time
import unittest

from src.queue.queue_backend import MemoryQueue
from src.queue.worker import QueueWorker


class WorkerTests(unittest.TestCase):
    def test_worker_processes_and_acks_task(self):
        queue = MemoryQueue()
        handled = []
        worker = QueueWorker(queue, lambda task, cancel: handled.append(task["task_id"]), poll_interval=0.01)
        queue.push({"task_id": "task-1"})
        worker.start()
        for _ in range(50):
            if handled:
                break
            time.sleep(0.01)
        worker.stop()
        self.assertEqual(handled, ["task-1"])
        self.assertEqual(queue.size(), 0)


if __name__ == "__main__":
    unittest.main()

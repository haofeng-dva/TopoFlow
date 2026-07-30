"""Queue worker lifecycle with cancellation and retry handling."""

import threading
import time
from typing import Callable, Optional


class QueueWorker:
    def __init__(self, queue, handler: Callable[[dict, threading.Event], None], poll_interval: float = 0.25):
        self.queue = queue
        self.handler = handler
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._cancellations: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="topoflow-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            event = self._cancellations.get(task_id)
            if event is None:
                event = threading.Event()
                self._cancellations[task_id] = event
            event.set()
        return True

    def _run(self) -> None:
        while not self._stop.is_set():
            task = self.queue.pop()
            if task is None:
                self._stop.wait(self.poll_interval)
                continue
            task_id = task["task_id"]
            with self._lock:
                cancel_event = self._cancellations.setdefault(task_id, threading.Event())
            try:
                if not cancel_event.is_set():
                    self.handler(task, cancel_event)
                self.queue.ack(task_id)
            except Exception:
                self.queue.nack(task_id)
            finally:
                with self._lock:
                    self._cancellations.pop(task_id, None)


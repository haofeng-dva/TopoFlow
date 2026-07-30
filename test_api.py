"""TopoFlow API 基础回归测试。"""

import unittest
from pathlib import Path
import shutil
import uuid

from src.api.server import PRESETS, TaskStore, _validate_extension, create_app
from src.config import Config


class ApiTests(unittest.TestCase):
    def test_task_store_lifecycle(self):
        store = TaskStore()
        self.addCleanup(store.close)
        created = store.create("task-1", {"filename": "hero.obj"})
        self.assertEqual(created["status"], "queued")
        updated = store.update("task-1", status="running")
        self.assertEqual(updated["status"], "running")
        self.assertEqual(store.get("task-1")["filename"], "hero.obj")
        self.assertEqual(len(store.list()), 1)
        cancelled = store.cancel("task-1")
        self.assertEqual(cancelled["status"], "cancelled")

    def test_extension_validation(self):
        self.assertEqual(_validate_extension("hero.OBJ"), ".obj")
        with self.assertRaises(ValueError):
            _validate_extension("hero.png")

    def test_app_registers_required_routes(self):
        temp_dir = Path(__file__).parent / ".test-tmp" / f"api-{uuid.uuid4().hex}"
        temp_dir.mkdir(parents=True)
        try:
            config = Config(output_dir=str(temp_dir))
            app = create_app(config)
            self.addCleanup(app.state.worker.stop)
            self.addCleanup(app.state.task_store.close)
            routes = {route.path for route in app.routes}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertIn("/health", routes)
        self.assertIn("/api/v1/presets", routes)
        self.assertIn("/api/v1/tasks", routes)
        self.assertIn("/api/v1/tasks/{task_id}", routes)
        self.assertIn("/api/v1/tasks/{task_id}/result", routes)
        self.assertIn("/api/v1/tasks/{task_id}/cancel", routes)
        self.assertIn("/api/v1/validate", routes)
        self.assertIn("ue5_nanite", PRESETS)


if __name__ == "__main__":
    unittest.main()

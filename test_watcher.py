"""TopoFlow Watch 模式回归测试。"""

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock

from src.config import Config
from src.pipeline.watcher import scan_once


class WatcherTests(unittest.TestCase):
    def temporary_directory(self, name):
        path = Path(__file__).parent / ".test-tmp" / f"{name}-{uuid.uuid4().hex}"
        path.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def test_scan_processes_new_file_and_skips_unchanged_file(self):
        watch_dir = self.temporary_directory("watch-input")
        output_dir = self.temporary_directory("watch-output")
        source = watch_dir / "hero.obj"
        source.write_text("v 0 0 0\n", encoding="utf-8")
        runner = Mock(return_value={"status": "quality_failed", "report_path": "report.json"})
        config = Config(output_dir=str(output_dir))

        first = scan_once(str(watch_dir), str(output_dir), config, runner=runner)
        second = scan_once(str(watch_dir), str(output_dir), config, runner=runner)

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        runner.assert_called_once()
        state_path = output_dir / "watch" / "watch_state.json"
        self.assertTrue(state_path.is_file())

    def test_scan_reprocesses_changed_file(self):
        watch_dir = self.temporary_directory("watch-change")
        output_dir = self.temporary_directory("watch-change-output")
        source = watch_dir / "hero.obj"
        source.write_text("v 0 0 0\n", encoding="utf-8")
        runner = Mock(return_value={"status": "passed", "report_path": "report.json"})
        config = Config(output_dir=str(output_dir))

        scan_once(str(watch_dir), str(output_dir), config, runner=runner)
        source.write_text("v 0 0 0\nv 1 0 0\n", encoding="utf-8")
        changed = scan_once(str(watch_dir), str(output_dir), config, runner=runner)

        self.assertEqual(len(changed), 1)
        self.assertEqual(runner.call_count, 2)

    def test_failure_is_recorded_and_not_retried_until_file_changes(self):
        watch_dir = self.temporary_directory("watch-failure")
        output_dir = self.temporary_directory("watch-failure-output")
        source = watch_dir / "broken.obj"
        source.write_text("invalid", encoding="utf-8")
        runner = Mock(side_effect=RuntimeError("bad mesh"))
        config = Config(output_dir=str(output_dir))

        first = scan_once(str(watch_dir), str(output_dir), config, runner=runner)
        second = scan_once(str(watch_dir), str(output_dir), config, runner=runner)

        self.assertEqual(first[0]["status"], "failed")
        self.assertEqual(first[0]["error"], "bad mesh")
        self.assertEqual(second, [])
        runner.assert_called_once()


if __name__ == "__main__":
    unittest.main()

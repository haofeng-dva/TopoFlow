"""TopoFlow Web UI 基础回归测试。"""

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from src.config import Config
from src.ui.webui import _gate_summary, _inspect_from_ui, _run_from_ui, create_ui


class WebUiTests(unittest.TestCase):
    def temporary_directory(self):
        path = Path(__file__).parent / ".test-tmp" / f"webui-{uuid.uuid4().hex}"
        path.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, path, True)
        return path

    @patch("src.ui.webui.run_model_pipeline")
    def test_run_handler_returns_status_report_and_download(self, run_pipeline):
        temp_dir = self.temporary_directory()
        report_path = temp_dir / "report.json"
        report_path.write_text(json.dumps({"task_id": "task-1"}), encoding="utf-8")
        run_pipeline.return_value = {
            "gate_a_passed": False,
            "report_path": str(report_path),
        }

        status, report, download = _run_from_ui(
            str(temp_dir / "source.obj"), "ue5_nanite", "自动", Config(output_dir=str(temp_dir))
        )

        self.assertIn("未通过", status)
        self.assertEqual(report["task_id"], "task-1")
        self.assertEqual(download, str(report_path))
        self.assertIsNone(run_pipeline.call_args.args[4])

    @patch("src.ui.webui.inspect_model")
    def test_inspect_handler_returns_report(self, inspect):
        temp_dir = self.temporary_directory()
        report_path = temp_dir / "inspect.json"
        inspect.return_value = {
            "status": "passed",
            "report_path": str(report_path),
            "gate_a": {"passed": True},
        }

        status, report, download = _inspect_from_ui(
            str(temp_dir / "source.obj"), Config(output_dir=str(temp_dir))
        )

        self.assertIn("通过", status)
        self.assertTrue(report["gate_a"]["passed"] )
        self.assertEqual(download, str(report_path))

    def test_create_ui_builds_without_launching_server(self):
        demo = create_ui(Config())
        self.addCleanup(demo.close)
        self.assertIsNotNone(demo)
        self.assertTrue(hasattr(demo, "launch"))

    def test_gate_summary_includes_gate_d(self):
        rows = _gate_summary({"quality_reports": {"gate_d_engine_import": {"passed": True, "metrics": {"bone_count": 24}}}})
        self.assertEqual(rows[-1][1], "通过")
        self.assertIn("bone_count", rows[-1][2])


if __name__ == "__main__":
    unittest.main()

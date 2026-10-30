import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock

from src.config import Config
from src.engine.tuanjie_project import ensure_validation_project
from src.pipeline.stage10_engine_validate import run
from src.tools.tuanjie import find_tuanjie


class TuanjieGateTests(unittest.TestCase):
    def temporary_directory(self):
        path = Path(__file__).parent / ".test-tmp" / f"tuanjie-{uuid.uuid4().hex}"
        path.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def test_project_template_contains_batch_validator(self):
        root = self.temporary_directory()
        project = Path(ensure_validation_project(str(root / "project")))
        self.assertTrue((project / "Assets/TopoFlow/Editor/TopoFlowBatchValidator.cs").is_file())
        self.assertTrue((project / "ProjectSettings/ProjectVersion.txt").is_file())
        self.assertEqual(json.loads((project / "Packages/manifest.json").read_text()), {"dependencies": {}})

    def test_gate_d_skips_when_editor_is_unavailable(self):
        config = Config(tuanjie_path=str(self.temporary_directory() / "missing.exe"))
        with mock.patch("src.pipeline.stage10_engine_validate.find_tuanjie", return_value=None):
            result = run(str(self.temporary_directory()), "task", "asset", config)
        self.assertIsNone(result["passed"])
        self.assertEqual(result["status"], "not_run")

    @unittest.skipUnless(find_tuanjie(), "团结引擎未安装（CI 环境跳过）")
    def test_installed_editor_is_discoverable(self):
        self.assertTrue(find_tuanjie())


if __name__ == "__main__":
    unittest.main()

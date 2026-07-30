"""Stage 0 配置边界与 Stage 2 策略确认测试。"""

import shutil
import unittest
import uuid
from pathlib import Path

from src.pipeline.stage0_generate import run as generate
from src.pipeline.stage2_confirm import run as confirm


class Stage0Stage2Tests(unittest.TestCase):
    def temporary_directory(self):
        path = Path(__file__).parent / ".test-tmp" / f"stage02-{uuid.uuid4().hex}"
        path.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def test_stage0_without_key_fails_before_network_call(self):
        image = self.temporary_directory() / "design.png"
        image.write_bytes(b"not-a-real-image")
        with self.assertRaisesRegex(RuntimeError, "Meshy API Key"):
            generate(str(image), {"api_keys": {"meshy": ""}})

    def test_stage2_applies_only_allowed_overrides(self):
        result = confirm(
            {"retopo_method": "meshlab", "target_face_count": 5000},
            {"total_faces": 10000},
            overrides={"retopo_method": "blender_remesh", "unknown": "ignored"},
        )
        self.assertEqual(result["retopo_method"], "blender_remesh")
        self.assertNotIn("unknown", result)
        self.assertEqual(result["confirmation_mode"], "confirmed")


if __name__ == "__main__":
    unittest.main()

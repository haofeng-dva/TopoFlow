"""Blender Stage 1-9 真实端到端测试。"""

import math
import shutil
import unittest
import uuid
from pathlib import Path

from src.config import Config
from src.pipeline.full_runner import run_full_model_pipeline
from src.tools.blender import find_blender


@unittest.skipUnless(find_blender(), "Blender 未安装")
class FullPipelineTests(unittest.TestCase):
    def temporary_directory(self):
        path = Path(__file__).parent / ".test-tmp" / f"full-{uuid.uuid4().hex}"
        path.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def create_quad_torus(self, path: Path):
        major, minor, radius, tube = 24, 12, 2.0, 0.6
        lines = []
        for i in range(major):
            u = 2 * math.pi * i / major
            for j in range(minor):
                v = 2 * math.pi * j / minor
                x = (radius + tube * math.cos(v)) * math.cos(u)
                y = (radius + tube * math.cos(v)) * math.sin(u)
                z = tube * math.sin(v)
                lines.append(f"v {x} {y} {z}")
        for i in range(major):
            for j in range(minor):
                a = i * minor + j + 1
                b = ((i + 1) % major) * minor + j + 1
                c = ((i + 1) % major) * minor + (j + 1) % minor + 1
                d = i * minor + (j + 1) % minor + 1
                lines.append(f"f {a} {b} {c} {d}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_full_pipeline_produces_uv_maps_and_three_gate_report(self):
        root = self.temporary_directory()
        source = root / "quad_torus.obj"
        self.create_quad_torus(source)
        config = Config(output_dir=str(root / "output"), blender_path=find_blender() or "")
        config.cache_enabled = False
        config.standards.uv_resolution = 128
        config.standards.bake_resolution = 128
        config.standards.gate_a_topology.max_topostrain_score = 100.0
        config.standards.gate_b_uv.min_first_quadrant_utilization = 0.25
        config.standards.gate_b_uv.max_stretch_pct = 60.0

        result = run_full_model_pipeline(
            str(source), config.output_dir, config, retopo_method="meshlab"
        )

        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["gate_a_passed"])
        self.assertTrue(result["gate_b_passed"])
        self.assertTrue(result["gate_c_passed"])
        output = Path(result["output_path"])
        self.assertTrue((output / "report.json").is_file())
        self.assertTrue(any("_normal" in path.name for path in output.rglob("*.png")))
        self.assertTrue(any("_basecolor" in path.name for path in output.rglob("*.png")))
        self.assertTrue(any("_roughness" in path.name for path in output.rglob("*.png")))


if __name__ == "__main__":
    unittest.main()

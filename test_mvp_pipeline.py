"""TopoFlow MVP 闭环自动测试。"""

import json
import os
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import trimesh

from src.config import Config
from src.pipeline import stage3_retopo, stage6_gate_b, stage8_gate_c, stage9_pack
from src.pipeline.mvp_runner import inspect_model, run_model_pipeline


class MvpPipelineTests(unittest.TestCase):
    @contextmanager
    def temporary_directory(self):
        temp_dir = Path(__file__).parent / ".test-tmp" / uuid.uuid4().hex
        temp_dir.mkdir(parents=True)
        try:
            yield str(temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    def test_meshlab_backend_exports_mesh_when_already_in_budget(self):
        with self.temporary_directory() as temp_dir:
            source = Path(temp_dir) / "source.obj"
            trimesh.creation.icosphere(subdivisions=1).export(source)

            result = stage3_retopo.run(
                str(source),
                {
                    "retopo_method": "meshlab",
                    "style_profile": "stylized_cartoon",
                    "target_face_count": 5000,
                },
            )

            self.assertIsNotNone(result)
            self.assertTrue(Path(result).is_file())
            output_mesh = trimesh.load(result, force="mesh")
            self.assertGreater(len(output_mesh.faces), 0)

    def test_pack_copies_real_artifacts_and_records_skipped_gates(self):
        with self.temporary_directory() as temp_dir:
            source = Path(temp_dir) / "source.obj"
            low = Path(temp_dir) / "low.obj"
            heatmap = Path(temp_dir) / "heatmap.obj"
            source.write_text("v 0 0 0\n", encoding="utf-8")
            low.write_text("v 0 0 0\n", encoding="utf-8")
            heatmap.write_text("v 0 0 0 1 0 0\n", encoding="utf-8")

            result = stage9_pack.run(
                task_id="task-1",
                asset_name="hero",
                high_poly_path=str(source),
                low_poly_path=str(low),
                heatmap_path=str(heatmap),
                maps={},
                gate_a={"passed": False},
                gate_b={"passed": None, "status": "not_run"},
                gate_c={"passed": None, "status": "not_run"},
                strategy={"target_face_count": 1000},
                output_dir=temp_dir,
                diagnosis={"total_faces": 1},
                duration_s=1.25,
                source_path=str(source),
            )

            report = json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))
            self.assertEqual(len(report["output_files"]), 3)
            self.assertEqual(report["timeline"]["total_duration_s"], 1.25)
            self.assertEqual(report["diagnosis"]["total_faces"], 1)
            for relative_path in report["output_files"]:
                self.assertTrue((Path(result["output_path"]) / relative_path).is_file())

    @patch("src.pipeline.mvp_runner.stage9_pack.run")
    @patch("src.pipeline.mvp_runner.stage4_gate_a.run")
    @patch("src.pipeline.mvp_runner.stage3_retopo.run")
    @patch("src.pipeline.mvp_runner.stage1_diagnose.run")
    def test_runner_reports_quality_failure_without_treating_it_as_crash(
        self, diagnose, retopo, gate_a, pack
    ):
        with self.temporary_directory() as temp_dir:
            source = Path(temp_dir) / "source.obj"
            source.write_text("v 0 0 0\n", encoding="utf-8")
            low = Path(temp_dir) / "stage3_low.obj"
            low.write_text("v 0 0 0\n", encoding="utf-8")
            report = Path(temp_dir) / "report.json"

            diagnose.return_value = ({"retopo_method": "meshlab"}, {"total_faces": 1})
            retopo.return_value = str(low)
            gate_a.return_value = {"passed": False, "metrics": {}, "heatmap_path": ""}
            pack.return_value = {"report_path": str(report), "output_path": temp_dir, "files": []}

            summary = run_model_pipeline(str(source), temp_dir, Config())

            self.assertEqual(summary["status"], "quality_failed")
            self.assertFalse(summary["gate_a_passed"])
            pack.assert_called_once()


    @patch("src.pipeline.mvp_runner.stage4_gate_a.run")
    @patch("src.pipeline.mvp_runner.stage1_diagnose.run")
    def test_inspect_model_writes_real_gate_a_report(self, diagnose, gate_a):
        with self.temporary_directory() as temp_dir:
            source = Path(temp_dir) / "source.obj"
            source.write_text("v 0 0 0\n", encoding="utf-8")
            destination = Path(temp_dir) / "inspect.json"
            diagnose.return_value = ({"retopo_method": "meshlab"}, {"total_faces": 1})
            gate_a.return_value = {"passed": False, "metrics": {"topostrain_score": 42.0}}

            result = inspect_model(str(source), str(destination), Config())

            self.assertEqual(result["status"], "quality_failed")
            self.assertTrue(destination.is_file())
            report = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(report["gate_a"]["metrics"]["topostrain_score"], 42.0)

    def test_missing_gate_inputs_never_report_success(self):
        gate_b = stage6_gate_b.run("missing.fbx", {}, {})
        gate_c = stage8_gate_c.run({}, {}, {})

        self.assertFalse(gate_b["passed"])
        self.assertEqual(gate_b["status"], "failed")
        self.assertFalse(gate_c["passed"])
        self.assertEqual(gate_c["status"], "failed")

if __name__ == "__main__":
    unittest.main()
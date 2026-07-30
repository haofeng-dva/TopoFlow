import unittest
import numpy as np

from src.pipeline.remediation import adapt_for_gate, adapt_for_gate_with_llm
from src.qc.topostrain import generate_heatmap_colors


class RemediationTests(unittest.TestCase):
    def test_gate_a_reduces_face_target(self):
        result = adapt_for_gate({"target_face_count": 10000}, "gate_a", {"metrics": {}}, 1)
        self.assertEqual(result["target_face_count"], 8000)

    def test_gate_b_increases_gap_and_changes_angle_for_stretch(self):
        result = adapt_for_gate({"uv_island_gap_px": 4}, "gate_b", {"metrics": {"stretch_pct": 12}}, 1)
        self.assertEqual(result["uv_island_gap_px"], 6)
        self.assertLess(result["uv_angle_limit"], 1.151917)

    def test_gate_c_increases_bake_quality(self):
        result = adapt_for_gate({}, "gate_c", {"metrics": {}}, 1)
        self.assertEqual(result["bake_margin"], 12)
        self.assertEqual(result["bake_samples"], 16)

    def test_heatmap_colors_are_deterministic(self):
        vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 2.0, 0.0]])
        faces = np.array([[0, 1, 2]])
        mask = np.array([True, False, True])
        first = generate_heatmap_colors(vertices, faces, mask, 75.0)
        second = generate_heatmap_colors(vertices, faces, mask, 75.0)
        np.testing.assert_array_equal(first, second)

    def test_llm_repairs_are_bounded_and_audited(self):
        from unittest import mock
        response = '{"bake_samples":9999,"cage_extrusion":-2,"command":"bad","analysis":"increase quality"}'
        with mock.patch("src.agents.llm_client.LLMClient.chat", return_value=response):
            result = adapt_for_gate_with_llm({}, "gate_c", {"metrics": {}}, 1, "temporary-key")
        self.assertEqual(result["bake_samples"], 256)
        self.assertEqual(result["cage_extrusion"], 0.001)
        self.assertNotIn("command", result)
        self.assertEqual(result["repair_source"], "deepseek")


if __name__ == "__main__":
    unittest.main()

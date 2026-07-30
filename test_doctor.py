import unittest
from unittest import mock
from src.config import Config
from src.tools.doctor import diagnose

class DoctorTests(unittest.TestCase):
    @mock.patch("src.tools.doctor.find_tuanjie", return_value="tuanjie.exe")
    @mock.patch("src.tools.doctor.find_blender", return_value="blender.exe")
    def test_diagnostics_report_ready_tools(self, _blender, _tuanjie):
        result = diagnose(Config(output_dir=".test-tmp/doctor"))
        self.assertTrue(result["ready_existing_models"])
        self.assertTrue(result["ready_gate_d"])
        self.assertEqual(result["uv_backend"], "blender_native")

if __name__ == "__main__": unittest.main()

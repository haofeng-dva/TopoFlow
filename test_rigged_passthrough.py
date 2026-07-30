import unittest
from unittest import mock

from src.engine.rigged_passthrough import validate_source


class RiggedPassthroughTests(unittest.TestCase):
    def test_missing_source_is_rejected_by_blender_import_builder(self):
        with self.assertRaises(Exception):
            validate_source("missing.glb", ".test-tmp", mock.Mock())


if __name__ == "__main__":
    unittest.main()

import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.knowledge.rule_dataset import build_dataset


class RuleDatasetTests(unittest.TestCase):
    def test_builds_jsonl_and_summary(self):
        root = Path(".test-tmp") / f"rules-{uuid.uuid4().hex}"
        self.addCleanup(shutil.rmtree, root, True)
        report_dir = root / "run"
        report_dir.mkdir(parents=True)
        (report_dir / "report.json").write_text(json.dumps({"task_id": "one", "quality_reports": {"gate_a_topology": {"passed": False, "errors": ["density"]}}}), encoding="utf-8")
        summary = build_dataset([str(root)], str(root / "data.jsonl"), str(root / "summary.json"))
        self.assertEqual(summary["records"], 1)
        self.assertEqual(summary["failure_modes"]["gate_a: density"], 1)


if __name__ == "__main__": unittest.main()

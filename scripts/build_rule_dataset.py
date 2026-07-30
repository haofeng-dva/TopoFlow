import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.knowledge.rule_dataset import build_dataset

summary = build_dataset(
    ["output", "output_mvp"],
    "knowledge_base/gate_runs.jsonl",
    "knowledge_base/gate_summary.json",
    "D:/Unity/Projects/TopoFlowValidation/TopoFlowResults",
)
print(json.dumps(summary, ensure_ascii=False, indent=2))

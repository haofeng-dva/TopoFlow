"""Build a local rule-learning dataset from pipeline audit reports."""

import json
from collections import Counter
from pathlib import Path


def _gate(report: dict, key: str) -> dict:
    return report.get("quality_reports", {}).get(key, {}) or {}


def record_from_report(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    gates = {
        "gate_a": _gate(report, "gate_a_topology"),
        "gate_b": _gate(report, "gate_b_uv"),
        "gate_c": _gate(report, "gate_c_bake"),
        "gate_d": _gate(report, "gate_d_engine_import") or report.get("gate_d", {}),
    }
    passed_values = [gate.get("passed") for gate in gates.values() if gate.get("passed") is not None]
    return {
        "report_path": str(path.resolve()),
        "task_id": report.get("task_id", path.parent.name),
        "asset_name": report.get("asset_name", path.parent.name),
        "source_path": report.get("source_path", ""),
        "mode": report.get("mode", "pipeline"),
        "passed": bool(passed_values) and all(passed_values),
        "gates": gates,
        "config": report.get("config_used", {}),
        "diagnosis": report.get("diagnosis", {}),
    }


def build_dataset(report_roots: list[str], dataset_path: str, summary_path: str, gate_d_results_dir: str = "") -> dict:
    records = []
    seen = set()
    for root in report_roots:
        for path in Path(root).glob("**/report.json"):
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                records.append(record_from_report(path))
            except Exception:
                continue
    gate_d_root = Path(gate_d_results_dir) if gate_d_results_dir else None
    if gate_d_root and gate_d_root.is_dir():
        for record in records:
            result_path = gate_d_root / f"{record['task_id']}.json"
            if not result_path.is_file():
                continue
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
                record["gates"]["gate_d"] = {
                    "passed": bool(result.get("passed")),
                    "status": result.get("status", "failed"),
                    "metrics": {key: result.get(key) for key in ("mesh_count", "skinned_mesh_count", "bone_count", "animation_clip_count", "material_count", "has_uv", "uv_required")},
                    "errors": result.get("errors", []),
                }
                values = [gate.get("passed") for gate in record["gates"].values() if gate.get("passed") is not None]
                record["passed"] = bool(values) and all(values)
            except Exception:
                continue
    destination = Path(dataset_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    failures = Counter()
    gate_runs = Counter()
    gate_passes = Counter()
    for record in records:
        for name, gate in record["gates"].items():
            if gate.get("passed") is None:
                continue
            gate_runs[name] += 1
            if gate.get("passed"):
                gate_passes[name] += 1
            else:
                errors = gate.get("errors", []) or ["threshold_violation"]
                for error in errors:
                    normalized = str(error).splitlines()[0][:160]
                    failures[f"{name}: {normalized}"] += 1
    summary = {
        "records": len(records),
        "fully_passed": sum(record["passed"] for record in records),
        "gate_runs": dict(gate_runs),
        "gate_passes": dict(gate_passes),
        "failure_modes": dict(failures.most_common()),
    }
    Path(summary_path).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary

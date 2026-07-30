import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.knowledge.rule_dataset import build_dataset
from src.pipeline.full_runner import run_full_model_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--output", default="output/benchmarks")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    config = load_config(args.config)
    config.standards.uv_resolution = args.resolution
    config.standards.bake_resolution = args.resolution
    extensions = {".obj", ".ply", ".stl", ".glb", ".gltf"}
    results = []
    for path in [p for p in Path(args.folder).rglob("*") if p.suffix.lower() in extensions][:args.limit]:
        try:
            results.append(run_full_model_pipeline(str(path), args.output, config, config.engine_preset, "meshlab"))
        except Exception as exc:
            results.append({"asset": str(path), "status": "crashed", "error": str(exc)})
    Path(args.output).mkdir(parents=True, exist_ok=True)
    (Path(args.output) / "benchmark_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    build_dataset([args.output], "knowledge_base/gate_runs.jsonl", "knowledge_base/gate_summary.json", config.tuanjie_project_dir + "/TopoFlowResults")


if __name__ == "__main__": main()


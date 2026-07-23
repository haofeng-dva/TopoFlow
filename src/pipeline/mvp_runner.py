"""TopoFlow 可运行的最小闭环：模型诊断、重拓扑、Gate A 与打包。"""

import json
import shutil
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from src.pipeline import stage1_diagnose, stage3_retopo, stage4_gate_a, stage9_pack


SUPPORTED_MODEL_EXTENSIONS = {".obj", ".ply", ".stl", ".glb", ".gltf"}


def config_to_dict(config) -> dict:
    """把 Config dataclass 转为现有 Stage 使用的字典结构。"""
    data = asdict(config)
    data["api_keys"] = {
        "deepseek": config.deepseek_key,
        "meshy": config.meshy_key,
        "openai": config.openai_key,
        "anthropic": config.anthropic_key,
    }
    return data


def run_model_pipeline(
    input_path: str,
    output_dir: str,
    config,
    preset: str = "ue5_nanite",
    retopo_method: str | None = None,
) -> dict:
    """运行已有 3D 模型到拓扑审计包的真实最小闭环。"""
    started_at = time.perf_counter()
    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"输入模型不存在: {source}")
    if source.suffix.lower() not in SUPPORTED_MODEL_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_MODEL_EXTENSIONS))
        raise ValueError(f"MVP 仅支持已有 3D 模型（{supported}），当前文件: {source.name}")

    task_id = f"{source.stem}_{uuid.uuid4().hex[:8]}"
    work_dir = Path(output_dir).expanduser().resolve() / ".work" / task_id
    work_dir.mkdir(parents=True, exist_ok=False)
    working_source = work_dir / f"stage0_source{source.suffix.lower()}"
    shutil.copy2(source, working_source)

    config_dict = config_to_dict(config)
    strategy, diagnosis = stage1_diagnose.run(str(working_source), config_dict)
    strategy["engine_preset"] = preset
    if retopo_method:
        strategy["retopo_method"] = retopo_method
    elif strategy.get("retopo_method") == "quadremesher":
        strategy["retopo_method"] = "meshlab"

    low_poly_path = stage3_retopo.run(str(working_source), strategy)
    if not low_poly_path:
        raise RuntimeError(
            f"重拓扑失败（后端: {strategy.get('retopo_method')}）。"
            "请安装 PyMeshLab，或选择已安装的 Instant Meshes/Blender/QuadRemesher。"
        )

    gate_a = stage4_gate_a.run(low_poly_path, strategy, config_dict)
    elapsed = round(time.perf_counter() - started_at, 3)
    skipped_gate = {"passed": None, "status": "not_run", "metrics": {}}
    package = stage9_pack.run(
        task_id=task_id,
        asset_name=source.stem,
        high_poly_path=str(working_source),
        low_poly_path=low_poly_path,
        heatmap_path=gate_a.get("heatmap_path", ""),
        maps={},
        gate_a=gate_a,
        gate_b=skipped_gate,
        gate_c=skipped_gate,
        strategy=strategy,
        output_dir=str(Path(output_dir).expanduser().resolve()),
        diagnosis=diagnosis,
        duration_s=elapsed,
        source_path=str(source),
    )

    summary = {
        "task_id": task_id,
        "status": "passed" if gate_a.get("passed") else "quality_failed",
        "gate_a_passed": bool(gate_a.get("passed")),
        "report_path": package["report_path"],
        "output_path": package["output_path"],
        "duration_s": elapsed,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary
"""已有 3D 模型的 Stage 1-9 完整执行器。"""

import json
import shutil
import time
import uuid
from pathlib import Path

from src.pipeline import (
    stage0_generate, stage1_diagnose, stage3_retopo, stage4_gate_a, stage5_uv,
    stage6_gate_b, stage7_bake, stage8_gate_c, stage9_pack, stage10_engine_validate,
)
from src.pipeline.mvp_runner import SUPPORTED_MODEL_EXTENSIONS, config_to_dict
from src.engine.presets import resolve_preset
from src.pipeline.remediation import adapt_for_gate_with_llm


def run_full_model_pipeline(
    input_path: str, output_dir: str, config, preset: str = "tuanjie_urp",
    retopo_method: str | None = None,
) -> dict:
    started_at = time.perf_counter()
    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"输入模型不存在: {source}")
    if source.suffix.lower() not in SUPPORTED_MODEL_EXTENSIONS:
        raise ValueError(f"不支持模型格式: {source.suffix}")

    task_id = f"{source.stem}_{uuid.uuid4().hex[:8]}"
    root = Path(output_dir).expanduser().resolve()
    work_dir = root / ".work" / task_id
    work_dir.mkdir(parents=True, exist_ok=False)
    high = work_dir / f"stage0_source{source.suffix.lower()}"
    shutil.copy2(source, high)
    config_dict = config_to_dict(config)
    strategy, diagnosis = stage1_diagnose.run(str(high), config_dict)
    engine = resolve_preset(preset)
    strategy.update({
        "engine_preset": preset,
        "engine": engine,
        "uv_packer": config.uv_packer,
        "blender_path": config.blender_path,
        "worker_timeout": config.worker_timeout,
        "uv_resolution": config.standards.uv_resolution,
        "bake_resolution": config.standards.bake_resolution,
        "normal_space": engine.get("normal_space", config.standards.normal_space),
    })
    if retopo_method:
        strategy["retopo_method"] = retopo_method
    elif strategy.get("retopo_method") == "quadremesher":
        strategy["retopo_method"] = "blender_remesh" if config.blender_path else "meshlab"

    low = stage3_retopo.run(str(high), strategy)
    if not low:
        raise RuntimeError("Stage 3 重拓扑失败")
    gate_a = stage4_gate_a.run(low, strategy, config_dict)
    for attempt in range(1, 3):
        if gate_a.get("passed"):
            break
        strategy = adapt_for_gate_with_llm(strategy, "gate_a", gate_a, attempt, config.deepseek_key)
        low = stage3_retopo.run(str(high), strategy)
        gate_a = stage4_gate_a.run(low, strategy, config_dict)
    skipped = {"passed": None, "status": "not_run", "metrics": {}}
    gate_b = skipped
    gate_c = skipped
    maps = {}
    uv_path = ""

    if gate_a.get("passed"):
        uv_path = stage5_uv.run(low, strategy) or ""
        if not uv_path:
            raise RuntimeError("Stage 5 UV 失败")
        gate_b = stage6_gate_b.run(uv_path, strategy, config_dict)
        for attempt in range(1, 3):
            if gate_b.get("passed"):
                break
            strategy = adapt_for_gate_with_llm(strategy, "gate_b", gate_b, attempt, config.deepseek_key)
            uv_path = stage5_uv.run(low, strategy) or ""
            gate_b = stage6_gate_b.run(uv_path, strategy, config_dict)
        if gate_b.get("passed"):
            maps = stage7_bake.run(uv_path, str(high), strategy, config_dict)
            gate_c = stage8_gate_c.run(maps, strategy, config_dict)
            for attempt in range(1, 3):
                if gate_c.get("passed"):
                    break
                strategy = adapt_for_gate_with_llm(strategy, "gate_c", gate_c, attempt, config.deepseek_key)
                maps = stage7_bake.run(uv_path, str(high), strategy, config_dict)
                gate_c = stage8_gate_c.run(maps, strategy, config_dict)

    elapsed = round(time.perf_counter() - started_at, 3)
    package = stage9_pack.run(
        task_id=task_id, asset_name=source.stem, high_poly_path=str(high),
        low_poly_path=uv_path or low, heatmap_path=gate_a.get("heatmap_path", ""),
        maps=maps, gate_a=gate_a, gate_b=gate_b, gate_c=gate_c, strategy=strategy,
        output_dir=str(root), diagnosis=diagnosis, duration_s=elapsed, source_path=str(source),
    )
    gate_d = skipped
    if gate_c.get("passed") and engine.get("engine") in {"unity", "tuanjie"} and config.tuanjie_path:
        gate_d = stage10_engine_validate.run(package["output_path"], task_id, source.stem, config)
    report_path = Path(package["report_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.setdefault("quality_reports", {})["gate_d_engine_import"] = gate_d
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    required_gates = [gate_a, gate_b, gate_c]
    if gate_d.get("passed") is not None:
        required_gates.append(gate_d)
    all_passed = all(gate.get("passed") is True for gate in required_gates)
    failed_gate = next((name for name, gate in (("gate_a", gate_a), ("gate_b", gate_b), ("gate_c", gate_c), ("gate_d", gate_d)) if gate.get("passed") is False), None)
    result = {
        "task_id": task_id, "status": "passed" if all_passed else "quality_failed",
        "failed_gate": failed_gate, "gate_a_passed": gate_a.get("passed"),
        "gate_b_passed": gate_b.get("passed"), "gate_c_passed": gate_c.get("passed"),
        "gate_d_passed": gate_d.get("passed"),
        "report_path": package["report_path"], "output_path": package["output_path"],
        "duration_s": elapsed,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def run_image_pipeline(
    image_path: str, output_dir: str, config, preset: str = "tuanjie_urp",
    retopo_method: str | None = None,
) -> dict:
    """调用 Stage 0 后继续执行已有模型完整管线。"""
    config_dict = config_to_dict(config)
    config_dict["output_dir"] = output_dir
    generated = stage0_generate.run(image_path, config_dict)
    if not generated:
        raise RuntimeError("Stage 0 未生成模型")
    result = run_full_model_pipeline(generated, output_dir, config, preset, retopo_method)
    result["source_image_path"] = str(Path(image_path).expanduser().resolve())
    result["generated_model_path"] = generated
    return result

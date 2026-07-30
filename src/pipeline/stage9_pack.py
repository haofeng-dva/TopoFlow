"""Stage 9: 最终打包与报告

输入: 全部中间产物
输出: 引擎就绪资产包 + report.json

打包内容:
  - _high/ 原始脏模
  - _low/ 低模 FBX + GLB
  - _maps/ 法线/AO/曲率贴图
  - _engine/ 引擎就绪包
  - report.json 全流程审计日志
"""

import json
import os
import shutil
from datetime import datetime
from src.engine.unity import write_unity_metadata
# dict is a builtin in Python 3.9+


def run(
    task_id: str,
    asset_name: str,
    high_poly_path: str,
    low_poly_path: str,
    heatmap_path: str,
    maps: dict,
    gate_a: dict,
    gate_b: dict,
    gate_c: dict,
    strategy: dict,
    output_dir: str,
    diagnosis: dict = None,
    duration_s: float = 0,
    source_path: str = "",
) -> dict:
    """执行 Stage 9 最终打包。

    Returns:
        打包结果: {output_path, report_path, files}
    """
    print(f"[Stage 9] 打包资产: {asset_name}")

    asset_dir = os.path.join(output_dir, f"{task_id}")
    os.makedirs(asset_dir, exist_ok=True)

    # 创建子目录
    for sub in ["_high", "_low", "_maps", "_engine"]:
        os.makedirs(os.path.join(asset_dir, sub), exist_ok=True)

    copied_files = []

    def copy_artifact(source: str, subdir: str, filename: str):
        if not source or not os.path.isfile(source):
            return ""
        destination = os.path.join(asset_dir, subdir, filename)
        shutil.copy2(source, destination)
        copied_files.append(os.path.relpath(destination, asset_dir).replace("\\", "/"))
        return destination

    source_extension = os.path.splitext(high_poly_path)[1].lower() or ".obj"
    low_extension = os.path.splitext(low_poly_path)[1].lower() or ".obj"
    copy_artifact(high_poly_path, "_high", f"{asset_name}_source{source_extension}")
    copy_artifact(low_poly_path, "_low", f"{asset_name}_low{low_extension}")
    copy_artifact(heatmap_path, "_low", f"{asset_name}_low_heatmap.obj")
    for map_name, map_path in (maps or {}).items():
        extension = os.path.splitext(map_path)[1].lower() if map_path else ".png"
        copy_artifact(map_path, "_maps", f"{asset_name}_{map_name}{extension}")

    engine_preset = strategy.get("engine", {})
    if engine_preset.get("engine") in {"unity", "tuanjie"}:
        engine_model = copy_artifact(low_poly_path, "_engine", f"{asset_name}.fbx")
        engine_maps = []
        for map_name, map_path in (maps or {}).items():
            extension = os.path.splitext(map_path)[1].lower() if map_path else ".png"
            copied = copy_artifact(map_path, "_engine", f"{asset_name}_{map_name}{extension}")
            if copied:
                engine_maps.append(copied)
        generated = write_unity_metadata(
            os.path.join(asset_dir, "_engine"),
            asset_name,
            [path for path in [engine_model, *engine_maps] if path],
            engine_preset,
        )
        copied_files.extend(
            os.path.relpath(path, asset_dir).replace("\\", "/") for path in generated
        )

    # 生成质检报告
    report = {
        "task_id": task_id,
        "asset_name": asset_name,
        "created_at": datetime.now().isoformat(),
        "timeline": {
            "total_duration_s": duration_s
        },
        "quality_reports": {
            "gate_a_topology": gate_a,
            "gate_b_uv": gate_b,
            "gate_c_bake": gate_c,
        },
        "diagnosis": diagnosis or {},
        "source_path": source_path or high_poly_path,
        "config_used": {
            "target_faces": strategy.get("target_face_count", 8000),
            "style_profile": strategy.get("style_profile", "stylized_cartoon"),
            "uv_resolution": strategy.get("uv_resolution", 2048),
            "bake_resolution": strategy.get("bake_resolution", 2048),
            "normal_space": strategy.get("normal_space", "directx"),
            "engine_preset": strategy.get("engine_preset", "unity"),
            "engine": engine_preset,
            "uv_backend": strategy.get("uv_backend", {}),
        },
        "output_files": copied_files,
    }

    report_path = os.path.join(asset_dir, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[Stage 9] 资产打包完成: {asset_dir}")
    return {
        "output_path": asset_dir,
        "report_path": report_path,
        "files": copied_files,
    }

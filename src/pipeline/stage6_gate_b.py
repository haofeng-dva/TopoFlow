"""Stage 6：使用 Blender 分析真实 UV 指标。"""

import json
from pathlib import Path

from src.tools.blender import run_blender_script


def run(uv_fbx_path: str, strategy: dict, config: dict) -> dict:
    source = Path(uv_fbx_path).expanduser().resolve()
    if not source.is_file():
        return {"passed": False, "status": "failed", "metrics": {}, "errors": [f"UV 文件不存在: {source}"]}
    report_path = source.parent / "stage6_uv_metrics.json"
    script = f'''
import bpy, json, math
from mathutils import geometry

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath={repr(str(source))})
mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
metrics = {{"mesh_count": len(mesh_objects), "triangle_count": 0, "uv_triangle_count": 0, "degenerate_uv_count": 0, "out_of_bounds_count": 0, "uv_area_sum": 0.0, "stretch_samples": []}}
for obj in mesh_objects:
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv_layer = mesh.uv_layers.active
    metrics["triangle_count"] += len(mesh.loop_triangles)
    if uv_layer is None:
        continue
    for tri in mesh.loop_triangles:
        uvs = [uv_layer.data[index].uv.copy() for index in tri.loops]
        metrics["uv_triangle_count"] += 1
        if any(uv.x < -1e-5 or uv.x > 1.00001 or uv.y < -1e-5 or uv.y > 1.00001 for uv in uvs):
            metrics["out_of_bounds_count"] += 1
        uv_area = abs((uvs[1].x-uvs[0].x)*(uvs[2].y-uvs[0].y) - (uvs[2].x-uvs[0].x)*(uvs[1].y-uvs[0].y)) * 0.5
        metrics["uv_area_sum"] += uv_area
        if uv_area < 1e-10:
            metrics["degenerate_uv_count"] += 1
            continue
        verts = [obj.matrix_world @ mesh.vertices[index].co for index in tri.vertices]
        area3d = geometry.area_tri(*verts)
        if area3d > 1e-12:
            metrics["stretch_samples"].append(uv_area / area3d)
ratios = metrics.pop("stretch_samples")
if ratios:
    ratios.sort()
    median = ratios[len(ratios)//2] or 1.0
    stretch_pct = sum(abs(value / median - 1.0) for value in ratios) * 100.0 / len(ratios)
else:
    stretch_pct = 100.0
metrics["stretch_pct"] = stretch_pct
metrics["utilization"] = min(1.0, metrics["uv_area_sum"])
metrics["has_uv"] = metrics["uv_triangle_count"] == metrics["triangle_count"] and metrics["triangle_count"] > 0
with open({repr(str(report_path))}, "w", encoding="utf-8") as output:
    json.dump(metrics, output, ensure_ascii=False, indent=2)
'''
    try:
        run_blender_script(
            script, str(source.parent),
            config.get("blender_path", strategy.get("blender_path", "")),
            int(config.get("worker_timeout", 3600)),
        )
        metrics = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"passed": False, "status": "failed", "metrics": {}, "errors": [str(exc)]}

    standards = config.get("standards", {}).get("gate_b_uv", {})
    min_utilization = float(standards.get("min_first_quadrant_utilization", 0.8))
    max_stretch = float(standards.get("max_stretch_pct", 3.0))
    passed = (
        metrics["has_uv"]
        and metrics["degenerate_uv_count"] == 0
        and metrics["out_of_bounds_count"] == 0
        and metrics["utilization"] >= min_utilization
        and metrics["stretch_pct"] <= max_stretch
    )
    errors = []
    if not metrics["has_uv"]: errors.append("部分网格缺少 UV")
    if metrics["degenerate_uv_count"]: errors.append("存在退化 UV 三角形")
    if metrics["out_of_bounds_count"]: errors.append("存在第一象限之外的 UV")
    if metrics["utilization"] < min_utilization: errors.append("UV 利用率不足")
    if metrics["stretch_pct"] > max_stretch: errors.append("UV 拉伸超过阈值")
    print(f"[Stage 6 Gate B] {'通过' if passed else '未通过'}: {metrics}")
    return {"passed": passed, "status": "passed" if passed else "quality_failed", "retry_count": 0, "metrics": metrics, "errors": errors}

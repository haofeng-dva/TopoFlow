"""Stage 5：使用 Blender 无头模式完成 UV 展开与 FBX 导出。"""

from pathlib import Path
from typing import Optional

from src.tools.blender import run_blender_script
from src.tools.uv_packers import resolve_uv_backend


def _import_statement(path: Path) -> str:
    source = repr(str(path))
    extension = path.suffix.lower()
    if extension == ".obj":
        return f"bpy.ops.wm.obj_import(filepath={source})"
    if extension == ".stl":
        return f"bpy.ops.wm.stl_import(filepath={source})"
    if extension == ".ply":
        return f"bpy.ops.wm.ply_import(filepath={source})"
    if extension in {".glb", ".gltf"}:
        return f"bpy.ops.import_scene.gltf(filepath={source})"
    if extension == ".fbx":
        return f"bpy.ops.import_scene.fbx(filepath={source})"
    raise ValueError(f"Blender UV 暂不支持输入格式: {extension}")


def run(low_poly_path: str, strategy: dict) -> Optional[str]:
    """执行 Blender Smart UV Project 并输出带 UV 的 FBX。"""
    source = Path(low_poly_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Stage 5 输入不存在: {source}")
    output = source.parent / "stage5_low_uv.fbx"
    uv_resolution = int(strategy.get("uv_resolution", 2048))
    backend = resolve_uv_backend(
        strategy.get("uv_packer", "auto"),
        strategy.get("blender_path", ""),
        min(120, int(strategy.get("worker_timeout", 3600))),
    )
    strategy["uv_backend"] = backend
    island_gap_px = int(strategy.get("uv_island_gap_px", 4))
    island_margin = max(0.001, min(0.1, island_gap_px / max(128, uv_resolution)))
    angle_limit = float(strategy.get("uv_angle_limit", 1.151917))
    import_statement = _import_statement(source)
    script = f'''
import bpy

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
{import_statement}
mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not mesh_objects:
    raise RuntimeError("导入文件中没有网格对象")
for obj in mesh_objects:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit={angle_limit}, island_margin={island_margin}, area_weight=0.0, correct_aspect=True, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.fbx(
    filepath={repr(str(output))},
    use_selection=True,
    apply_unit_scale=True,
    bake_space_transform=False,
    add_leaf_bones=False,
    path_mode="AUTO",
)
'''
    print(f"[Stage 5] Blender UV 展开: {source}, 分辨率={uv_resolution}")
    run_blender_script(
        script,
        str(source.parent),
        strategy.get("blender_path", ""),
        int(strategy.get("worker_timeout", 3600)),
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Blender 未生成 Stage 5 FBX")
    print(f"[Stage 5] 输出带 UV 低模: {output}")
    return str(output)

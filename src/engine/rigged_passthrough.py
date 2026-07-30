"""Preserve rigs and animations while converting source assets to FBX."""

import json
import shutil
import uuid
from pathlib import Path

from src.engine.unity import write_unity_metadata
from src.pipeline.stage5_uv import _import_statement
from src.pipeline.stage10_engine_validate import run as run_gate_d
from src.tools.blender import run_blender_script


def validate_source(source_path: str, output_dir: str, config) -> dict:
    source = Path(source_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    task_id = f"{source.stem}_rigged_{uuid.uuid4().hex[:8]}"
    package = Path(output_dir).expanduser().resolve() / task_id
    engine_dir = package / "_engine"
    engine_dir.mkdir(parents=True, exist_ok=True)
    fbx_path = engine_dir / f"{source.stem}.fbx"
    script = f'''
import bpy
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
{_import_statement(source)}
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.fbx(
    filepath={repr(str(fbx_path))}, use_selection=True, apply_unit_scale=True,
    add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True,
    path_mode="COPY", embed_textures=True,
)
'''
    run_blender_script(script, str(package), config.blender_path, config.worker_timeout)
    if not fbx_path.is_file():
        raise RuntimeError("Blender did not create rig-preserving FBX")
    write_unity_metadata(str(engine_dir), source.stem, [str(fbx_path)], {
        "name": "tuanjie_rigged_passthrough", "engine": "tuanjie", "normal_space": "opengl",
    })
    result = run_gate_d(str(package), task_id, source.stem, config)
    report = {"task_id": task_id, "source_path": str(source), "mode": "rigged_passthrough", "gate_d": result}
    report_path = package / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    result.update({"task_id": task_id, "output_path": str(package), "report_path": str(report_path)})
    return result

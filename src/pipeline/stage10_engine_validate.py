"""Stage 10 / Gate D: validate the packaged asset in Tuanjie Engine."""

import json
import shutil
import subprocess
from pathlib import Path

from src.engine.tuanjie_project import ensure_validation_project
from src.tools.tuanjie import find_tuanjie


def run(package_dir: str, task_id: str, asset_name: str, config) -> dict:
    executable = find_tuanjie(getattr(config, "tuanjie_path", ""))
    if not executable:
        return {"passed": None, "status": "not_run", "metrics": {}, "errors": ["Tuanjie editor not found"]}
    project_dir = Path(getattr(config, "tuanjie_project_dir", r"D:\Unity\Projects\TopoFlowValidation"))
    ensure_validation_project(str(project_dir))
    source = Path(package_dir) / "_engine"
    if not source.is_dir():
        return {"passed": False, "status": "failed", "metrics": {}, "errors": ["Engine package not found"]}
    destination = project_dir / "Assets" / "TopoFlow" / "Imports" / task_id
    imports_root = project_dir / "Assets" / "TopoFlow" / "Imports"
    for editor_dir in imports_root.glob("*/Editor"):
        shutil.rmtree(editor_dir, ignore_errors=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("Editor", "*.cs"))
    manifest = destination / "topoflow_unity.json"
    if not manifest.is_file():
        return {"passed": False, "status": "failed", "metrics": {}, "errors": ["Engine manifest not found"]}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["files"] = [str(path.resolve()) for path in destination.iterdir() if path.is_file() and path.suffix.lower() in {".fbx", ".png", ".jpg", ".jpeg", ".tga"}]
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    result_path = project_dir / "TopoFlowResults" / f"{task_id}.json"
    log_path = project_dir / "TopoFlowResults" / f"{task_id}.log"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable, "-batchmode", "-nographics", "-quit", "-projectPath", str(project_dir),
        "-executeMethod", "TopoFlow.Editor.TopoFlowBatchValidator.Run",
        "-topoflowManifest", str(manifest), "-topoflowResult", str(result_path),
        "-logFile", str(log_path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=int(getattr(config, "worker_timeout", 3600)))
    except Exception as exc:
        return {"passed": False, "status": "failed", "metrics": {}, "errors": [str(exc)], "log_path": str(log_path)}
    if not result_path.is_file():
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:] if log_path.is_file() else completed.stderr[-4000:]
        return {"passed": False, "status": "failed", "metrics": {"exit_code": completed.returncode}, "errors": ["Tuanjie did not produce Gate D result", tail], "log_path": str(log_path)}
    result = json.loads(result_path.read_text(encoding="utf-8"))
    return {
        "passed": bool(result.get("passed")), "status": result.get("status", "failed"),
        "metrics": {key: result.get(key) for key in ("mesh_count", "skinned_mesh_count", "bone_count", "animation_clip_count", "material_count", "has_uv", "uv_required", "normal_map_imported", "model_path", "material_path", "prefab_path")},
        "errors": result.get("errors", []), "result_path": str(result_path), "log_path": str(log_path),
    }

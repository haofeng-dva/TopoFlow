"""UV packing backend discovery and selection."""

import json
from pathlib import Path

from src.tools.blender import run_blender_script


def detect_uvpackmaster(blender_path: str = "", timeout: int = 120) -> dict:
    probe_dir = Path.cwd() / ".temp" / "uvpackmaster_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    result_path = probe_dir / "result.json"
    script = f'''
import bpy, json
matches = []
for module in bpy.context.preferences.addons.keys():
    if "uvpackmaster" in module.lower() or "uvpm" in module.lower():
        addon = bpy.context.preferences.addons.get(module)
        version = getattr(getattr(addon, "preferences", None), "version", "")
        matches.append({{"module": module, "version": str(version)}})
with open({repr(str(result_path))}, "w", encoding="utf-8") as handle:
    json.dump({{"available": bool(matches), "addons": matches}}, handle)
'''
    try:
        run_blender_script(script, str(probe_dir), blender_path, timeout)
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except Exception as exc:
        data = {"available": False, "addons": [], "error": str(exc)}
    finally:
        result_path.unlink(missing_ok=True)
    data["detected_backend"] = "uvpackmaster4" if data.get("available") else None
    data["backend"] = "blender_native"
    data["integration_status"] = "detected_not_invoked" if data.get("available") else "fallback"
    return data


def resolve_uv_backend(requested: str, blender_path: str = "", timeout: int = 120) -> dict:
    requested = (requested or "auto").lower()
    detection = detect_uvpackmaster(blender_path, timeout) if requested in {"auto", "uvpackmaster4"} else {"available": False, "addons": [], "backend": "blender_native"}
    if requested == "uvpackmaster4" and not detection.get("available"):
        detection["fallback_reason"] = "UVPackmaster 4 is not enabled in Blender"
    detection["requested"] = requested
    return detection

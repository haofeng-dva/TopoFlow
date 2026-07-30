"""Environment diagnostics used by CLI, UI, and packaged builds."""

import json
import platform
import shutil
import sys
from pathlib import Path

from src.tools.blender import find_blender
from src.tools.tuanjie import find_tuanjie


def diagnose(config) -> dict:
    output = Path(config.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    blender = find_blender(config.blender_path)
    tuanjie = find_tuanjie(config.tuanjie_path)
    return {
        "python": sys.version.split()[0], "platform": platform.platform(),
        "blender": blender, "tuanjie": tuanjie, "output_dir": str(output),
        "output_writable": _writable(output),
        "disk_free_gb": round(shutil.disk_usage(output).free / (1024 ** 3), 2),
        "uv_backend": "blender_native", "meshy_configured": bool(config.meshy_key),
        "ready_existing_models": bool(blender), "ready_gate_d": bool(tuanjie),
    }


def _writable(path: Path) -> bool:
    try:
        probe = path / ".topoflow_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def print_diagnostics(config) -> int:
    result = diagnose(config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready_existing_models"] and result["output_writable"] else 1


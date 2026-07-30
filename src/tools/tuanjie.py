"""Tuanjie Engine editor discovery helpers."""

import shutil
from pathlib import Path
from typing import Optional


def find_tuanjie(configured_path: str = "") -> Optional[str]:
    candidates = []
    if configured_path:
        candidates.append(Path(configured_path).expanduser())
    executable = shutil.which("Tuanjie") or shutil.which("Tuanjie.exe")
    if executable:
        candidates.append(Path(executable))
    editors_root = Path(r"D:\Unity\TuanjieEditors")
    if editors_root.is_dir():
        candidates.extend(editors_root.glob(r"*\Editor\Tuanjie.exe"))
    candidates.extend([
        Path(r"D:\Unity\TuanjieEditors\2022.3.62t11\Editor\Tuanjie.exe"),
        Path(r"C:\Program Files\Tuanjie\Editor\Tuanjie.exe"),
    ])
    valid = [candidate.resolve() for candidate in candidates if candidate.is_file()]
    if not valid:
        return None
    return str(max(valid, key=lambda path: path.stat().st_mtime))


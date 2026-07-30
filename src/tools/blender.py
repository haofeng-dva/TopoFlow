"""Blender 可执行文件发现与无头脚本执行。"""

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional


def find_blender(configured_path: str = "") -> Optional[str]:
    candidates = []
    if configured_path:
        candidates.append(Path(configured_path).expanduser())
    from_path = shutil.which("blender") or shutil.which("blender.exe")
    if from_path:
        candidates.append(Path(from_path))
    candidates.extend([
        Path(r"E:\blender\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"),
    ])
    if os.name == "nt":
        try:
            import winreg
            for hive, key_path in [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]:
                try:
                    with winreg.OpenKey(hive, key_path) as root:
                        for index in range(winreg.QueryInfoKey(root)[0]):
                            with winreg.OpenKey(root, winreg.EnumKey(root, index)) as subkey:
                                name = str(winreg.QueryValueEx(subkey, "DisplayName")[0])
                                if "blender" not in name.lower():
                                    continue
                                location = Path(winreg.QueryValueEx(subkey, "InstallLocation")[0])
                                candidates.append(location / "blender.exe")
                except OSError:
                    continue
        except ImportError:
            pass
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def run_blender_script(
    script: str,
    work_dir: str,
    configured_path: str = "",
    timeout: int = 3600,
) -> subprocess.CompletedProcess:
    executable = find_blender(configured_path)
    if not executable:
        raise RuntimeError("未找到 Blender；请在 config.toml 的 [tools].blender_path 中配置")
    directory = Path(work_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    script_path = directory / f"topoflow_blender_{uuid.uuid4().hex}.py"
    script_path.write_text(script, encoding="utf-8")
    try:
        result = subprocess.run(
            [executable, "--background", "--factory-startup", "--python", str(script_path)],
            cwd=str(directory),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    finally:
        script_path.unlink(missing_ok=True)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-4000:]
        raise RuntimeError(f"Blender 执行失败（exit={result.returncode}）: {tail}")
    return result

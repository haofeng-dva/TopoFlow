"""TopoFlow 文件夹监控模式。"""

import json
import time
from pathlib import Path
from typing import Callable, Optional

from src.pipeline.mvp_runner import SUPPORTED_MODEL_EXTENSIONS, run_model_pipeline


def _fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def _load_state(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def scan_once(
    folder: str,
    output_dir: str,
    config,
    preset: Optional[str] = None,
    retopo_method: Optional[str] = None,
    runner: Callable = run_model_pipeline,
) -> list[dict]:
    """扫描并处理新增或发生变化的模型文件。"""
    watch_dir = Path(folder).expanduser().resolve()
    if not watch_dir.is_dir():
        raise FileNotFoundError(f"监控目录不存在: {watch_dir}")

    destination = Path(output_dir).expanduser().resolve() / "watch"
    state_path = destination / "watch_state.json"
    state = _load_state(state_path)
    results = []

    candidates = sorted(
        path for path in watch_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_MODEL_EXTENSIONS
    )
    for source in candidates:
        fingerprint = _fingerprint(source)
        key = str(source)
        if state.get(key, {}).get("fingerprint") == fingerprint:
            continue

        try:
            result = runner(
                str(source),
                str(destination / "assets"),
                config,
                preset or config.engine_preset,
                retopo_method,
            )
            entry = {
                "fingerprint": fingerprint,
                "status": result["status"],
                "report_path": result["report_path"],
                "error": None,
            }
        except Exception as exc:
            entry = {
                "fingerprint": fingerprint,
                "status": "failed",
                "report_path": None,
                "error": str(exc),
            }
        state[key] = entry
        results.append({"source_path": key, **entry})
        _save_state(state_path, state)

    return results


def watch_folder(
    folder: str,
    output_dir: str,
    config,
    poll_interval: float = 2.0,
    preset: Optional[str] = None,
    retopo_method: Optional[str] = None,
) -> None:
    """持续监控目录，按 Ctrl+C 安全退出。"""
    watch_dir = Path(folder).expanduser().resolve()
    if not watch_dir.is_dir():
        raise FileNotFoundError(f"监控目录不存在: {watch_dir}")

    print(f"[Watch] 正在监控: {watch_dir}")
    print("[Watch] 按 Ctrl+C 停止")
    try:
        while True:
            for result in scan_once(folder, output_dir, config, preset, retopo_method):
                if result["status"] == "failed":
                    print(f"[Watch] 处理失败: {result['source_path']} - {result['error']}")
                else:
                    print(f"[Watch] 处理完成: {result['source_path']} - {result['status']}")
            time.sleep(max(0.2, poll_interval))
    except KeyboardInterrupt:
        print("[Watch] 已停止")

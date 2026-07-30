"""基于 JSON 文件的确定性缓存。"""

import hashlib
import json
from pathlib import Path
from typing import Optional


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"不可序列化类型: {type(value).__name__}")


def file_digest(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def cache_key(namespace: str, source_path: str, parameters: dict) -> str:
    payload = {
        "namespace": namespace,
        "source_sha256": file_digest(source_path),
        "parameters": parameters,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class FileCache:
    def __init__(self, root: str, max_entries: int = 20):
        self.root = Path(root).expanduser().resolve()
        self.max_entries = max(1, max_entries)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace: str, key: str) -> Path:
        return self.root / namespace / f"{key}.json"

    def get(self, namespace: str, key: str) -> Optional[dict]:
        path = self._path(namespace, key)
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            path.touch()
            return value
        except (OSError, json.JSONDecodeError):
            return None

    def set(self, namespace: str, key: str, value: dict) -> Path:
        path = self._path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
        temporary.replace(path)
        self.prune(namespace)
        return path

    def prune(self, namespace: str) -> None:
        directory = self.root / namespace
        if not directory.is_dir():
            return
        entries = sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        for stale in entries[self.max_entries:]:
            stale.unlink(missing_ok=True)

"""Meshy Image-to-3D API 适配器。"""

import base64
import json
import mimetypes
import time
import urllib.request
from pathlib import Path


class MeshyClient:
    base_url = "https://api.meshy.ai/openapi/v1/image-to-3d"

    def __init__(self, api_key: str, timeout: int = 3600, poll_interval: float = 5.0):
        if not api_key:
            raise RuntimeError("Stage 0 需要 Meshy API Key，请配置 [api_keys].meshy")
        self.api_key = api_key
        self.timeout = timeout
        self.poll_interval = poll_interval

    def _request(self, url: str, method: str = "GET", payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url, data=data, method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _image_data_uri(self, image_path: str) -> str:
        path = Path(image_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"输入设计图不存在: {path}")
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def generate(self, image_path: str, output_path: str, target_polycount: int = 100000) -> str:
        created = self._request(self.base_url, "POST", {
            "image_url": self._image_data_uri(image_path),
            "enable_pbr": True,
            "should_remesh": True,
            "target_polycount": int(target_polycount),
            "should_texture": True,
            "target_formats": ["glb"],
        })
        task_id = created.get("result")
        if not task_id:
            raise RuntimeError(f"Meshy 未返回任务 ID: {created}")
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            task = self._request(f"{self.base_url}/{task_id}")
            status = task.get("status")
            if status == "SUCCEEDED":
                model_url = task.get("model_urls", {}).get("glb")
                if not model_url:
                    raise RuntimeError("Meshy 任务成功但没有 GLB 下载地址")
                destination = Path(output_path).expanduser().resolve()
                destination.parent.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(model_url, timeout=120) as response:
                    destination.write_bytes(response.read())
                return str(destination)
            if status in {"FAILED", "CANCELED"}:
                message = task.get("task_error", {}).get("message") or status
                raise RuntimeError(f"Meshy 生成失败: {message}")
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Meshy 任务超时: {task_id}")

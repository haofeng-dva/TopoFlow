"""Stage 0：设计图生成 3D 高模。"""

from pathlib import Path
from typing import Optional

from src.providers.meshy import MeshyClient


def run(image_path: str, config: dict) -> Optional[str]:
    source = Path(image_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"设计图不存在: {source}")
    api_key = config.get("api_keys", {}).get("meshy") or config.get("meshy_key", "")
    output_dir = Path(config.get("output_dir", "./output")).expanduser().resolve() / "stage0"
    output_path = output_dir / f"{source.stem}_raw.glb"
    client = MeshyClient(
        api_key, timeout=int(config.get("worker_timeout", 3600)),
        poll_interval=float(config.get("meshy_poll_interval", 5.0)),
    )
    print(f"[Stage 0] Meshy 图生 3D: {source}")
    return client.generate(
        str(source), str(output_path), int(config.get("stage0_target_polycount", 100000))
    )

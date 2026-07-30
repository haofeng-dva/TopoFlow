"""Stage 8：贴图文件、分辨率和像素质量检查。"""

from pathlib import Path

import numpy as np


def _load_image(path: str):
    from PIL import Image
    image = Image.open(path).convert("RGB")
    return image, np.asarray(image, dtype=np.float32) / 255.0


def run(maps: dict, strategy: dict, config: dict) -> dict:
    required = ("normal", "ao", "curvature")
    missing = [name for name in required if not maps.get(name) or not Path(maps[name]).is_file()]
    if missing:
        return {
            "passed": False, "status": "failed", "retry_count": 0, "metrics": {},
            "errors": [f"缺少贴图: {', '.join(missing)}"],
        }
    try:
        loaded = {name: _load_image(maps[name]) for name in required}
    except Exception as exc:
        return {"passed": False, "status": "failed", "retry_count": 0, "metrics": {}, "errors": [str(exc)]}

    sizes = {name: image.size for name, (image, _) in loaded.items()}
    resolution_match = len(set(sizes.values())) == 1
    normal = loaded["normal"][1]
    ao = loaded["ao"][1].mean(axis=2)
    curvature = loaded["curvature"][1].mean(axis=2)

    normal_dx = np.abs(np.diff(normal, axis=1)).mean(axis=2) if normal.shape[1] > 1 else np.zeros((normal.shape[0], 1))
    normal_dy = np.abs(np.diff(normal, axis=0)).mean(axis=2) if normal.shape[0] > 1 else np.zeros((1, normal.shape[1]))
    normal_seam_ratio = float((np.count_nonzero(normal_dx > 0.35) + np.count_nonzero(normal_dy > 0.35)) / max(1, normal_dx.size + normal_dy.size))
    normal_blue_mean = float(normal[:, :, 2].mean())

    ao_dx = np.abs(np.diff(ao, axis=1)).mean() if ao.shape[1] > 1 else 0.0
    ao_dy = np.abs(np.diff(ao, axis=0)).mean() if ao.shape[0] > 1 else 0.0
    ao_noise_level = float((ao_dx + ao_dy) * 0.5)
    ao_dead_black_ratio = float(np.mean(ao < 0.01))
    curvature_dynamic_range = float(curvature.max() - curvature.min())

    metrics = {
        "resolutions": {name: list(size) for name, size in sizes.items()},
        "resolution_match": resolution_match,
        "normal_seam_ratio": round(normal_seam_ratio, 6),
        "normal_blue_mean": round(normal_blue_mean, 6),
        "ao_noise_level": round(ao_noise_level, 6),
        "ao_dead_black_ratio": round(ao_dead_black_ratio, 6),
        "curvature_dynamic_range": round(curvature_dynamic_range, 6),
        "color_space_metadata_valid": None,
        "color_space_note": "PNG 不保证携带可验证的工作色彩空间，按贴图角色记录预期值",
        "expected_normal_space": strategy.get("normal_space", "directx"),
        "pbr_channels": sorted(name for name in maps if name in {"basecolor", "metallic", "roughness", "emission"}),
        "pbr_complete": all(maps.get(name) and Path(maps[name]).is_file() for name in ("basecolor", "metallic", "roughness", "emission")),
    }
    passed = (
        resolution_match
        and normal_blue_mean > 0.35
        and normal_seam_ratio < 0.1
        and ao_noise_level < 0.25
        and ao_dead_black_ratio < 0.95
        and metrics["pbr_complete"]
    )
    errors = []
    if not resolution_match: errors.append("贴图分辨率不一致")
    if normal_blue_mean <= 0.35: errors.append("法线贴图蓝通道异常")
    if normal_seam_ratio >= 0.1: errors.append("法线高差异边缘过多")
    if ao_noise_level >= 0.25: errors.append("AO 高频噪声过高")
    if ao_dead_black_ratio >= 0.95: errors.append("AO 接近全黑")
    if not metrics["pbr_complete"]: errors.append("PBR 通道不完整")
    print(f"[Stage 8 Gate C] {'通过' if passed else '未通过'}: {metrics}")
    return {
        "passed": passed, "status": "passed" if passed else "quality_failed",
        "retry_count": 0, "metrics": metrics, "errors": errors,
    }

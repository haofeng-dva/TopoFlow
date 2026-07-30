"""Stage 2：策略确认和用户覆盖。"""

from pathlib import Path


def run(
    strategy: dict, diagnosis: dict, auto_pilot: bool = False, overrides: dict | None = None,
    guide_curves_path: str = "", freeze_mask_path: str = "",
) -> dict:
    confirmed = dict(strategy)
    if overrides:
        allowed = {
            "style_profile", "retopo_method", "target_face_count", "uv_resolution",
            "bake_resolution", "normal_space", "preserve_features",
        }
        confirmed.update({key: value for key, value in overrides.items() if key in allowed})
    for label, path in (("guide_curves_path", guide_curves_path), ("freeze_mask_path", freeze_mask_path)):
        if path:
            resolved = Path(path).expanduser().resolve()
            if not resolved.is_file():
                raise FileNotFoundError(f"用户引导文件不存在: {resolved}")
            confirmed[label] = str(resolved)
    confirmed["confirmation_mode"] = "auto_pilot" if auto_pilot else "confirmed"
    confirmed["diagnosis_face_count"] = diagnosis.get("total_faces", 0)
    print(f"[Stage 2] 策略已确认: {confirmed['confirmation_mode']}")
    return confirmed

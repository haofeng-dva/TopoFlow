"""Engine preset definitions used by export, bake, and packaging stages."""

PRESETS = {
    "unity": {"engine": "unity", "normal_space": "opengl", "model_format": "fbx", "scale_factor": 1.0, "up_axis": "y", "forward_axis": "z"},
    "unity_urp": {"engine": "unity", "render_pipeline": "urp", "normal_space": "opengl", "model_format": "fbx", "scale_factor": 1.0, "up_axis": "y", "forward_axis": "z"},
    "unity_hdrp": {"engine": "unity", "render_pipeline": "hdrp", "normal_space": "opengl", "model_format": "fbx", "scale_factor": 1.0, "up_axis": "y", "forward_axis": "z"},
    "tuanjie": {"engine": "tuanjie", "unity_compatibility": "2022_lts", "normal_space": "opengl", "model_format": "fbx", "scale_factor": 1.0, "up_axis": "y", "forward_axis": "z"},
    "tuanjie_urp": {"engine": "tuanjie", "unity_compatibility": "2022_lts", "render_pipeline": "urp", "normal_space": "opengl", "model_format": "fbx", "scale_factor": 1.0, "up_axis": "y", "forward_axis": "z"},
    "ue5_nanite": {"engine": "unreal", "normal_space": "directx", "model_format": "fbx", "scale_factor": 1.0, "up_axis": "z", "forward_axis": "x"},
    "mobile": {"engine": "generic_mobile", "normal_space": "opengl", "model_format": "fbx", "scale_factor": 1.0, "up_axis": "y", "forward_axis": "z"},
}


def resolve_preset(name: str) -> dict:
    resolved_name = name if name in PRESETS else "unity"
    return {"name": resolved_name, **PRESETS[resolved_name]}

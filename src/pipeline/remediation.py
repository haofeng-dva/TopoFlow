"""Deterministic parameter adaptations for quality-gate retries."""

import json


def adapt_for_gate(strategy: dict, gate_name: str, gate_result: dict, attempt: int) -> dict:
    adapted = dict(strategy)
    metrics = gate_result.get("metrics", {})
    adapted["repair_attempt"] = attempt
    adapted["repair_gate"] = gate_name
    if gate_name == "gate_a":
        current = int(adapted.get("target_face_count", 8000))
        adapted["target_face_count"] = max(500, int(current * 0.8))
        adapted["voxel_size"] = float(adapted.get("voxel_size", 0.02)) * 0.85
    elif gate_name == "gate_b":
        current_gap = int(adapted.get("uv_island_gap_px", 4))
        adapted["uv_island_gap_px"] = max(current_gap + 2, int(current_gap * 1.5))
        if metrics.get("stretch_pct", 0) > 3:
            adapted["uv_angle_limit"] = max(0.7, float(adapted.get("uv_angle_limit", 1.151917)) * 0.9)
    elif gate_name == "gate_c":
        adapted["bake_margin"] = min(64, int(adapted.get("bake_margin", 8)) + 4)
        adapted["bake_samples"] = min(64, int(adapted.get("bake_samples", 8)) * 2)
        adapted["cage_extrusion"] = min(0.1, float(adapted.get("cage_extrusion", 0.02)) * 1.25)
    return adapted


LIMITS = {
    "target_face_count": (500, 200000, int),
    "voxel_size": (0.001, 1.0, float),
    "uv_island_gap_px": (1, 128, int),
    "uv_angle_limit": (0.3, 1.57, float),
    "bake_margin": (1, 128, int),
    "bake_samples": (1, 256, int),
    "cage_extrusion": (0.001, 0.25, float),
}


def adapt_for_gate_with_llm(strategy: dict, gate_name: str, gate_result: dict, attempt: int, api_key: str = "") -> dict:
    adapted = adapt_for_gate(strategy, gate_name, gate_result, attempt)
    adapted["repair_source"] = "rules"
    if not api_key:
        return adapted
    try:
        from src.agents.llm_client import LLMClient
        system = """你是3D资产管线质量修复专家。只输出JSON对象。允许字段仅为 target_face_count、voxel_size、uv_island_gap_px、uv_angle_limit、bake_margin、bake_samples、cage_extrusion、analysis。不要输出命令、路径或代码。"""
        prompt = f"Gate={gate_name}\nStrategy={adapted}\nFailure={gate_result}\n输出安全修复参数。"
        proposal = json.loads(LLMClient(provider="deepseek", api_key=api_key).chat(system, prompt, json_mode=True))
        accepted = {}
        for key, value in proposal.items():
            if key not in LIMITS:
                continue
            lower, upper, converter = LIMITS[key]
            converted = converter(value)
            accepted[key] = max(lower, min(upper, converted))
        if accepted:
            adapted.update(accepted)
            adapted["repair_source"] = "deepseek"
            adapted["repair_analysis"] = str(proposal.get("analysis", ""))[:500]
    except Exception as exc:
        adapted["repair_llm_error"] = type(exc).__name__
    return adapted

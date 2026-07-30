"""
TopoFlow — LangGraph 管线主图

10 Stage 状态图；生产 CLI 使用 full_runner，状态图保留给 Agent 编排。
"""

from langgraph.graph import StateGraph, START, END
from src.config import load_config as _load_config
from .state import PipelineState
from . import stage0_generate, stage1_diagnose, stage2_confirm, stage3_retopo
from . import stage4_gate_a, stage5_uv, stage6_gate_b, stage7_bake, stage8_gate_c, stage9_pack


def build_pipeline(config_path: str = "config.toml"):
    """构建 LangGraph 管线。"""
    cfg = _load_config(config_path)
    cfg_dict = {
        "deepseek_key": cfg.deepseek_key,
        "api_keys": {"deepseek": cfg.deepseek_key, "meshy": cfg.meshy_key},
        "output_dir": cfg.output_dir,
        "blender_path": cfg.blender_path,
        "worker_timeout": cfg.worker_timeout,
        "standards": {
            "gate_a_topology": {
                "max_triangle_pct": cfg.standards.gate_a_topology.max_triangle_pct,
                "max_face_density_variance": cfg.standards.gate_a_topology.max_face_density_variance,
                "require_watertight": cfg.standards.gate_a_topology.require_watertight,
                "max_topostrain_score": cfg.standards.gate_a_topology.max_topostrain_score,
            },
            "gate_b_uv": {
                "min_island_gap_px": cfg.standards.gate_b_uv.min_island_gap_px,
                "min_first_quadrant_utilization": cfg.standards.gate_b_uv.min_first_quadrant_utilization,
                "max_stretch_pct": cfg.standards.gate_b_uv.max_stretch_pct,
            }
        }
    }

    workflow = StateGraph(PipelineState)

    # ========== Stage 节点 ==========

    def node_stage0(state: PipelineState) -> PipelineState:
        result = stage0_generate.run(state.input_image_path, cfg_dict)
        if result:
            state.high_poly_path = result
        state.current_stage = 1
        return state

    def node_stage1(state: PipelineState) -> PipelineState:
        strategy, diagnosis = stage1_diagnose.run(state.high_poly_path, cfg_dict)
        state.strategy = strategy
        state.diagnosis = diagnosis
        state.current_stage = 2
        return state

    def node_stage2(state: PipelineState) -> PipelineState:
        strategy = stage2_confirm.run(state.strategy, state.diagnosis, False)
        state.strategy = strategy
        state.current_stage = 3
        return state

    def node_stage3(state: PipelineState) -> PipelineState:
        result = stage3_retopo.run(state.high_poly_path, state.strategy)
        if result:
            state.low_poly_path = result
        state.current_stage = 4
        return state

    def node_stage4(state: PipelineState) -> PipelineState:
        result = stage4_gate_a.run(state.low_poly_path, state.strategy, cfg_dict)
        state.gate_a_result = result
        if result.get("heatmap_path"):
            state.heatmap_path = result["heatmap_path"]
        if result.get("passed"):
            state.low_poly_passed_path = state.low_poly_path
            state.current_stage = 5
        return state

    def node_stage5(state: PipelineState) -> PipelineState:
        state.strategy["blender_path"] = cfg.blender_path
        state.strategy["worker_timeout"] = cfg.worker_timeout
        result = stage5_uv.run(state.low_poly_passed_path, state.strategy)
        if result:
            state.low_poly_uv_path = result
        state.current_stage = 6
        return state

    def node_stage6(state: PipelineState) -> PipelineState:
        result = stage6_gate_b.run(state.low_poly_uv_path, state.strategy, cfg_dict)
        state.gate_b_result = result
        state.current_stage = 7 if result.get("passed") else 6
        return state

    def node_stage7(state: PipelineState) -> PipelineState:
        maps = stage7_bake.run(state.low_poly_uv_path, state.high_poly_path, state.strategy, cfg_dict)
        state.normal_map_path = maps.get("normal", "")
        state.ao_map_path = maps.get("ao", "")
        state.curvature_map_path = maps.get("curvature", "")
        state.current_stage = 8
        return state

    def node_stage8(state: PipelineState) -> PipelineState:
        maps = {"normal": state.normal_map_path, "ao": state.ao_map_path, "curvature": state.curvature_map_path}
        result = stage8_gate_c.run(maps, state.strategy, cfg_dict)
        state.gate_c_result = result
        state.current_stage = 9 if result.get("passed") else 8
        return state

    def node_stage9(state: PipelineState) -> PipelineState:
        maps = {"normal": state.normal_map_path, "ao": state.ao_map_path, "curvature": state.curvature_map_path}
        result = stage9_pack.run(
            state.task_id, state.asset_name,
            state.high_poly_path, state.low_poly_path,
            state.heatmap_path, maps,
            state.gate_a_result, state.gate_b_result, state.gate_c_result,
            state.strategy, state.output_dir,
        )
        state.report = result
        state.completed = True
        state.current_stage = 10
        return state

    # ========== 注册节点 ==========
    for name, fn in [
        ("stage0", node_stage0), ("stage1", node_stage1), ("stage2", node_stage2),
        ("stage3", node_stage3), ("stage4", node_stage4), ("stage5", node_stage5),
        ("stage6", node_stage6), ("stage7", node_stage7), ("stage8", node_stage8),
        ("stage9", node_stage9),
    ]:
        workflow.add_node(name, fn)

    # ========== 质检条件边（Gate A/B/C） ==========
    def _gate_router(state, gate_key, retry_stage):
        result = getattr(state, gate_key, None)
        if result and result.get("passed"):
            state.retry_count = 0
            return "next"
        state.retry_count += 1
        if state.retry_count > 2:
            state.paused = True
            return "pause"
        return "retry"

    workflow.add_conditional_edges("stage4",
        lambda s: _gate_router(s, "gate_a_result", "stage3"),
        {"next": "stage5", "retry": "stage3", "pause": END})

    workflow.add_conditional_edges("stage6",
        lambda s: _gate_router(s, "gate_b_result", "stage5"),
        {"next": "stage7", "retry": "stage5", "pause": END})

    workflow.add_conditional_edges("stage8",
        lambda s: _gate_router(s, "gate_c_result", "stage7"),
        {"next": "stage9", "retry": "stage7", "pause": END})

    # ========== 主线流程 ==========
    workflow.add_edge(START, "stage0")
    workflow.add_edge("stage0", "stage1")
    workflow.add_edge("stage1", "stage2")
    workflow.add_edge("stage2", "stage3")
    workflow.add_edge("stage3", "stage4")
    workflow.add_edge("stage5", "stage6")
    workflow.add_edge("stage7", "stage8")
    workflow.add_edge("stage9", END)

    return workflow.compile(), cfg_dict

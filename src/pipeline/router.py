"""TopoFlow 管线节点工具函数"""

from .state import PipelineState


def should_retry(state: PipelineState, max_retries: int = 2) -> str:
    """质检失败后判断是重试还是暂停"""
    if state.retry_count >= max_retries:
        return "pause"
    return "retry"


def should_skip_stage2(state: PipelineState) -> str:
    """Auto-pilot 模式下跳过 Stage 2 人工确认"""
    if state.strategy.get("auto_pilot_eligible", False):
        return "skip"
    return "confirm"


def stage_router(state: PipelineState) -> str:
    """主流程路由：根据当前 Stage 决定下一个节点"""
    mapping = {
        0: "stage0",
        1: "stage1",
        2: "stage2",
        3: "stage3",
        4: "stage4",
        5: "stage5",
        6: "stage6",
        7: "stage7",
        8: "stage8",
        9: "stage9",
    }
    return mapping.get(state.current_stage, "__end__")

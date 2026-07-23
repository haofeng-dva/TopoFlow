"""TopoFlow 管线状态定义"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PipelineState:
    """LangGraph 状态节点，贯穿 10 个 Stage"""
    # === 任务信息 ===
    task_id: str = ""
    asset_name: str = ""
    input_image_path: str = ""          # 原始设计图路径
    high_poly_path: str = ""            # Stage 0 输出的脏模/高模
    low_poly_path: str = ""             # Stage 3 输出的低模
    low_poly_uv_path: str = ""          # Stage 5 输出的带 UV 低模
    low_poly_passed_path: str = ""      # Gate A 通过的低模
    heatmap_path: str = ""              # TopoVision 热力图 OBJ

    # === 诊断信息 ===
    diagnosis: dict = field(default_factory=dict)       # Stage 1 诊断报告
    strategy: dict = field(default_factory=dict)         # LLM 输出策略 JSON

    # === 质检结果 ===
    gate_a_result: Optional[dict] = None
    gate_b_result: Optional[dict] = None
    gate_c_result: Optional[dict] = None

    # === 贴图 ===
    normal_map_path: str = ""
    ao_map_path: str = ""
    curvature_map_path: str = ""

    # === 流程控制 ===
    current_stage: int = 0
    retry_count: int = 0                # 当前 Gate 重试次数
    error_message: str = ""
    paused: bool = False                # 是否暂停等待人工介入
    completed: bool = False

    # === 输出 ===
    output_dir: str = ""
    report: dict = field(default_factory=dict)

"""TopoFlow Gradio Web UI。"""

import json
import shutil
from pathlib import Path
from typing import Optional

from src.config import Config
from src.pipeline.full_runner import run_full_model_pipeline
from src.pipeline.mvp_runner import inspect_model, run_model_pipeline
from src.tools.blender import find_blender
from src.tools.tuanjie import find_tuanjie
from src.tools.uv_packers import detect_uvpackmaster


def _file_path(value) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return getattr(value, "name", str(value))


def _load_report(report_path: str) -> dict:
    path = Path(report_path)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _tool_status(config: Config) -> dict:
    blender = find_blender(config.blender_path)
    tuanjie = find_tuanjie(config.tuanjie_path)
    uv = detect_uvpackmaster(blender or "", 60) if blender else {"available": False}
    return {
        "Blender": blender or "未安装",
        "团结引擎": tuanjie or "未安装",
        "UV 后端": "UVPackmaster 4" if uv.get("available") else "Blender Native",
        "Meshy": "已配置" if config.meshy_key else "接口待 Key",
    }


def _gate_summary(report: dict) -> list[list]:
    quality = report.get("quality_reports", {})
    rows = []
    for key, label in (("gate_a_topology", "Gate A 拓扑"), ("gate_b_uv", "Gate B UV"), ("gate_c_bake", "Gate C 烘焙"), ("gate_d_engine_import", "Gate D 引擎")):
        gate = quality.get(key, {})
        passed = gate.get("passed")
        status = "通过" if passed is True else "失败" if passed is False else "未运行"
        rows.append([label, status, json.dumps(gate.get("metrics", {}), ensure_ascii=False)])
    return rows


def _zip_output(output_path: str) -> str:
    path = Path(output_path)
    return shutil.make_archive(str(path), "zip", root_dir=str(path)) if path.is_dir() else ""


def _run_product_ui(file_value, preset: str, retopo_method: str, config: Config):
    source = _file_path(file_value)
    if not source:
        raise ValueError("请先上传 3D 模型")
    method = None if retopo_method == "自动" else retopo_method
    result = run_full_model_pipeline(source, config.output_dir, config, preset, method)
    report = _load_report(result["report_path"])
    status = "✅ 全部质量门通过" if result.get("status") == "passed" else f"⚠️ 未通过：{result.get('failed_gate') or '质量检查'}"
    return status, _gate_summary(report), report, result["report_path"], _zip_output(result.get("output_path", ""))


def _run_from_ui(file_value, preset: str, retopo_method: str, config: Config, full: bool = False):
    source = _file_path(file_value)
    if not source:
        raise ValueError("请先上传 3D 模型")
    method = None if retopo_method == "自动" else retopo_method
    runner = run_full_model_pipeline if full else run_model_pipeline
    result = runner(source, config.output_dir, config, preset, method)
    report = _load_report(result["report_path"])
    status = "✅ Gate A 通过" if result["gate_a_passed"] else "⚠️ 管线完成，但 Gate A 未通过"
    download = _zip_output(result.get("output_path", "")) if full else result["report_path"]
    return status, report, download


def _inspect_from_ui(file_value, config: Config):
    source = _file_path(file_value)
    if not source:
        raise ValueError("请先上传 3D 模型")
    source_path = Path(source)
    report_path = Path(config.output_dir) / "inspections" / f"{source_path.stem}_inspect.json"
    result = inspect_model(source, str(report_path), config)
    status = "✅ Gate A 通过" if result["status"] == "passed" else "⚠️ Gate A 未通过"
    return status, result, result["report_path"]


def create_ui(config: Optional[Config] = None):
    """创建模型处理与质检界面。"""
    try:
        import gradio as gr
    except ImportError as exc:
        raise RuntimeError("启动 Web UI 需要安装 gradio") from exc

    cfg = config or Config()
    with gr.Blocks(title="TopoFlow") as demo:
        gr.Markdown("# TopoFlow\n已有 3D 模型的诊断、重拓扑、Gate A 与报告工具。")
        gr.Markdown("可选择快速 MVP 或完整 Stage 1-9；完整模式使用 Blender 执行 UV、烘焙和 Gate B/C。")

        with gr.Tab("运行 MVP 管线"):
            gr.JSON(value=_tool_status(cfg), label="工具状态（UV 默认 Blender Native）")
            run_file = gr.File(
                label="上传模型",
                file_types=[".obj", ".ply", ".stl", ".glb", ".gltf"],
                type="filepath",
            )
            with gr.Row():
                preset = gr.Dropdown(
                    choices=["tuanjie_urp", "tuanjie", "unity", "unity_urp", "unity_hdrp", "ue5_nanite", "mobile"],
                    value=cfg.engine_preset if cfg.engine_preset in {"tuanjie_urp", "tuanjie", "unity", "unity_urp", "unity_hdrp", "ue5_nanite", "mobile"} else "tuanjie_urp",
                    label="引擎预设",
                )
                retopo = gr.Dropdown(
                    choices=["自动", "meshlab", "instant_meshes", "blender_remesh", "quadremesher"],
                    value="自动",
                    label="重拓扑后端",
                )
            full_mode = gr.Checkbox(value=False, label="运行完整 Stage 1-9（需要 Blender，耗时更长）")
            run_button = gr.Button("开始处理", variant="primary")
            run_status = gr.Markdown()
            run_report = gr.JSON(label="处理报告")
            run_download = gr.File(label="下载报告")
            run_button.click(
                fn=lambda file_value, preset_value, method, full: _run_from_ui(file_value, preset_value, method, cfg, full),
                inputs=[run_file, preset, retopo, full_mode],
                outputs=[run_status, run_report, run_download],
            )

        with gr.Tab("仅质检"):
            inspect_file = gr.File(
                label="上传模型",
                file_types=[".obj", ".ply", ".stl", ".glb", ".gltf"],
                type="filepath",
            )
            inspect_button = gr.Button("执行 Stage 1 + Gate A", variant="primary")
            inspect_status = gr.Markdown()
            inspect_report = gr.JSON(label="质检报告")
            inspect_download = gr.File(label="下载报告")
            inspect_button.click(
                fn=lambda file_value: _inspect_from_ui(file_value, cfg),
                inputs=[inspect_file],
                outputs=[inspect_status, inspect_report, inspect_download],
            )

    return demo


def launch(config: Optional[Config] = None):
    """启动本地 Web UI。"""
    print("[WebUI] 启动: http://127.0.0.1:7860")
    create_ui(config).launch(server_name="127.0.0.1", server_port=7860, inbrowser=False, show_error=True)

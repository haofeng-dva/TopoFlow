"""
TopoFlow — 3D 资产管线 Agent

使用方式：
  topoflow                          # 启动 Web UI
  topoflow run --input design.png   # CLI 模式运行
  topoflow serve --port 8080        # 启动 API 服务
  topoflow watch --folder ./in/     # 监控文件夹
"""

import argparse
import sys
import os

# 确保 src 在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_config


def main():
    parser = argparse.ArgumentParser(
        prog="topoflow",
        description="TopoFlow — 从设计图到引擎就绪资产的工业级全自动管线 Agent"
    )
    parser.add_argument("--config", default="config.toml", help="配置文件路径")
    parser.add_argument("--mode", choices=["web", "cli", "api", "watch", "inspect"],
                        help="运行模式（覆盖配置文件）")

    sub = parser.add_subparsers(dest="command")

    # topoflow run --input xxx --output xxx
    run_parser = sub.add_parser("run", help="CLI 模式运行管线")
    run_parser.add_argument("--input", required=True, help="输入 3D 模型路径（OBJ/PLY/STL/GLB/GLTF）")
    run_parser.add_argument("--output", default="./output", help="输出目录")
    run_parser.add_argument("--preset", default="ue5_nanite", help="引擎预设")
    run_parser.add_argument(
        "--retopo-method",
        choices=["meshlab", "instant_meshes", "blender_remesh", "quadremesher"],
        default=None,
        help="重拓扑后端；默认使用策略结果，商业后端会自动回退到 MeshLab",
    )

    # topoflow serve --port 8080
    serve_parser = sub.add_parser("serve", help="启动 API 服务")
    serve_parser.add_argument("--port", type=int, default=8080, help="监听端口")
    serve_parser.add_argument("--host", default="127.0.0.1", help="监听地址")

    # topoflow watch --folder ./incoming/
    watch_parser = sub.add_parser("watch", help="监控文件夹")
    watch_parser.add_argument("--folder", required=True, help="监控目录路径")

    # topoflow inspect --model model.obj
    inspect_parser = sub.add_parser("inspect", help="仅执行质检")
    inspect_parser.add_argument("--model", required=True, help="模型文件路径")
    inspect_parser.add_argument("--output", default="./inspect_report.json", help="质检报告输出路径")

    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.command == "run":
        exit_code = _run_pipeline(args.input, args.output, args.preset, cfg, args.retopo_method)
        if exit_code:
            raise SystemExit(exit_code)
    elif args.command == "serve":
        _start_api(args.host, args.port, cfg)
    elif args.command == "watch":
        _start_watch(args.folder, cfg)
    elif args.command == "inspect":
        _run_inspect(args.model, args.output, cfg)
    else:
        _start_webui(cfg)


def _run_pipeline(input_path: str, output_dir: str, preset: str, cfg, retopo_method=None):
    """CLI 模式：运行已有模型的最小真实闭环。"""
    print(f"[TopoFlow] 开始处理: {input_path}")
    print(f"[TopoFlow] 引擎预设: {preset}")
    print(f"[TopoFlow] 输出目录: {output_dir}")
    print("[TopoFlow] MVP 管线运行中：诊断 → 重拓扑 → Gate A → 打包")
    from src.pipeline.mvp_runner import run_model_pipeline

    try:
        result = run_model_pipeline(input_path, output_dir, cfg, preset, retopo_method)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[TopoFlow] 运行失败: {exc}", file=sys.stderr)
        return 1
    print(f"[TopoFlow] 管线完成: {result['report_path']}")
    return 0


def _start_api(host: str, port: int, cfg):
    """API Server 模式：启动 FastAPI 服务"""
    print(f"[TopoFlow] 启动 API 服务: http://{host}:{port}")
    # TODO: 启动 FastAPI
    # uvicorn.run(src.api.server.app, host=host, port=port)
    print("[TopoFlow] API 服务已停止")


def _start_watch(folder: str, cfg):
    """Watch 模式：监控文件夹"""
    print(f"[TopoFlow] 监控文件夹: {folder}")
    # TODO: 实现文件系统监控
    print("[TopoFlow] 监控已停止")


def _run_inspect(model_path: str, output_path: str, cfg):
    """仅质检模式：执行三重 Gate 质检"""
    print(f"[TopoFlow] 质检模型: {model_path}")
    # TODO: 执行质检并输出报告
    print(f"[TopoFlow] 质检报告: {output_path}")


def _start_webui(cfg):
    """交互模式：启动 Gradio Web UI"""
    print("[TopoFlow] 启动 Web UI...")
    # TODO: 启动 Gradio
    # from src.ui.webui import launch
    # launch(cfg)
    print("[TopoFlow] Web UI 已关闭")


if __name__ == "__main__":
    main()

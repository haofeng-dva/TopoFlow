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
    run_parser.add_argument("--preset", default="tuanjie_urp", help="引擎预设")
    run_parser.add_argument("--full", action="store_true", help="运行 Stage 1-9 完整管线（需要 Blender）")
    run_parser.add_argument(
        "--retopo-method",
        choices=["meshlab", "instant_meshes", "blender_remesh", "quadremesher"],
        default=None,
        help="重拓扑后端；默认使用策略结果，商业后端会自动回退到 MeshLab",
    )

    generate_parser = sub.add_parser("generate", help="设计图生成 3D 并运行完整管线（需要 Meshy Key）")
    generate_parser.add_argument("--input", required=True, help="输入设计图路径")
    generate_parser.add_argument("--output", default="./output", help="输出目录")
    generate_parser.add_argument("--preset", default="tuanjie_urp", help="引擎预设")
    generate_parser.add_argument("--retopo-method", choices=["meshlab", "instant_meshes", "blender_remesh", "quadremesher"], default=None)

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
        exit_code = _run_pipeline(args.input, args.output, args.preset, cfg, args.retopo_method, args.full)
        if exit_code:
            raise SystemExit(exit_code)
    elif args.command == "generate":
        from src.pipeline.full_runner import run_image_pipeline
        try:
            result = run_image_pipeline(args.input, args.output, cfg, args.preset, args.retopo_method)
            print(f"[TopoFlow] 图生 3D 管线完成: {result['report_path']}")
        except (FileNotFoundError, ValueError, RuntimeError, TimeoutError) as exc:
            print(f"[TopoFlow] 图生 3D 失败: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
    elif args.command == "serve":
        _start_api(args.host, args.port, cfg)
    elif args.command == "watch":
        _start_watch(args.folder, cfg)
    elif args.command == "inspect":
        exit_code = _run_inspect(args.model, args.output, cfg)
        if exit_code:
            raise SystemExit(exit_code)
    else:
        _start_webui(cfg)


def _run_pipeline(input_path: str, output_dir: str, preset: str, cfg, retopo_method=None, full=False):
    """CLI 模式：运行已有模型的最小真实闭环。"""
    print(f"[TopoFlow] 开始处理: {input_path}")
    print(f"[TopoFlow] 引擎预设: {preset}")
    print(f"[TopoFlow] 输出目录: {output_dir}")
    print("[TopoFlow] MVP 管线运行中：诊断 → 重拓扑 → Gate A → 打包")
    if full:
        print("[TopoFlow] 完整管线运行中：诊断 → 重拓扑 → Gate A → UV → Gate B → 烘焙 → Gate C → 打包")
        from src.pipeline.full_runner import run_full_model_pipeline as runner
    else:
        from src.pipeline.mvp_runner import run_model_pipeline as runner

    try:
        result = runner(input_path, output_dir, cfg, preset, retopo_method)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[TopoFlow] 运行失败: {exc}", file=sys.stderr)
        return 1
    print(f"[TopoFlow] 管线完成: {result['report_path']}")
    return 0


def _start_api(host: str, port: int, cfg):
    """API Server 模式：启动 FastAPI 服务。"""
    print(f"[TopoFlow] 启动 API 服务: http://{host}:{port}")
    from src.api.server import start_server

    try:
        start_server(host, port, cfg)
    except RuntimeError as exc:
        print(f"[TopoFlow] API 启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _start_watch(folder: str, cfg):
    """Watch 模式：持续处理目录中的新增或变化模型。"""
    from src.pipeline.watcher import watch_folder

    try:
        watch_folder(folder, cfg.output_dir, cfg)
    except FileNotFoundError as exc:
        print(f"[TopoFlow] Watch 启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _run_inspect(model_path: str, output_path: str, cfg):
    """仅质检模式：执行当前已实现的 Stage 1 与 Gate A。"""
    print(f"[TopoFlow] 质检模型: {model_path}")
    from src.pipeline.mvp_runner import inspect_model

    try:
        result = inspect_model(model_path, output_path, cfg)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[TopoFlow] 质检失败: {exc}", file=sys.stderr)
        return 1

    print(f"[TopoFlow] 质检报告: {result['report_path']}")
    if result["status"] != "passed":
        print("[TopoFlow] Gate A 未通过", file=sys.stderr)
        return 2
    return 0


def _start_webui(cfg):
    """交互模式：启动 Gradio Web UI。"""
    from src.ui.webui import launch

    try:
        launch(cfg)
    except RuntimeError as exc:
        print(f"[TopoFlow] Web UI 启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

"""FastAPI 服务 — REST API 层"""

from typing import Optional


# TODO: 实际启动时 import 真实的 FastAPI
# from fastapi import FastAPI, UploadFile, File, BackgroundTasks
# app = FastAPI(title="TopoFlow API", version="1.0.0")


def create_app():
    """创建 FastAPI 应用实例。

    端点:
      POST /api/v1/tasks        — 提交任务
      GET  /api/v1/tasks/{id}   — 查询状态
      GET  /api/v1/tasks/{id}/result  — 下载结果
      POST /api/v1/webhook      — 注册回调
      GET  /api/v1/presets      — 获取预设列表
      POST /api/v1/validate     — 仅执行质检
    """
    # TODO: 实现各端点
    # TODO: 异步任务队列
    # TODO: 文件上传/下载
    # TODO: Webhook 回调
    pass


def start_server(host: str = "127.0.0.1", port: int = 8080):
    """启动 API 服务。"""
    print(f"[API] 启动服务: http://{host}:{port}")
    # TODO: uvicorn.run(app, host=host, port=port)

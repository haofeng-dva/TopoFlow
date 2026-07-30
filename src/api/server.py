"""TopoFlow FastAPI 服务。"""

import json
import shutil
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Optional

from src.config import Config
from src.pipeline.full_runner import run_full_model_pipeline
from src.pipeline.mvp_runner import SUPPORTED_MODEL_EXTENSIONS, config_to_dict, inspect_model, run_model_pipeline
from src.queue.queue_backend import create_queue_backend
from src.queue.worker import QueueWorker


PRESETS = {
    "ue5_nanite": {"engine": "ue5", "normal_space": "directx"},
    "unity": {"engine": "unity", "normal_space": "opengl"},
    "unity_urp": {"engine": "unity", "normal_space": "opengl"},
    "unity_hdrp": {"engine": "unity", "normal_space": "opengl"},
    "tuanjie": {"engine": "tuanjie", "normal_space": "opengl"},
    "tuanjie_urp": {"engine": "tuanjie", "normal_space": "opengl"},
    "mobile": {"engine": "mobile", "normal_space": "opengl"},
}


class TaskStore:
    """线程安全的 SQLite 任务状态存储。"""

    def __init__(self, database_path: str = ":memory:"):
        self.database_path = database_path
        self._lock = threading.Lock()
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        self._connection.commit()

    def create(self, task_id: str, payload: dict) -> dict:
        task = {"task_id": task_id, "status": "queued", **payload}
        encoded = json.dumps(task, ensure_ascii=False)
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO tasks(task_id, payload) VALUES (?, ?)",
                (task_id, encoded),
            )
            self._connection.commit()
        return dict(task)

    def update(self, task_id: str, **changes) -> dict:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if not row:
                raise KeyError(task_id)
            task = json.loads(row[0])
            task.update(changes)
            self._connection.execute(
                "UPDATE tasks SET payload = ? WHERE task_id = ?",
                (json.dumps(task, ensure_ascii=False), task_id),
            )
            self._connection.commit()
            return dict(task)

    def get(self, task_id: str) -> Optional[dict]:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT payload FROM tasks ORDER BY rowid DESC LIMIT ?", (max(1, min(limit, 1000)),)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def cancel(self, task_id: str) -> dict:
        task = self.get(task_id)
        if not task:
            raise KeyError(task_id)
        if task.get("status") in {"passed", "quality_failed", "failed", "cancelled"}:
            return task
        return self.update(task_id, status="cancelled", progress=task.get("progress", 0), error=None)

    def recover_incomplete(self) -> int:
        recovered = 0
        with self._lock:
            rows = self._connection.execute("SELECT task_id, payload FROM tasks").fetchall()
            for task_id, encoded in rows:
                task = json.loads(encoded)
                if task.get("status") not in {"queued", "running"}:
                    continue
                task["status"] = "interrupted"
                task["error"] = "服务重启时任务尚未完成，请重新提交"
                self._connection.execute(
                    "UPDATE tasks SET payload = ? WHERE task_id = ?",
                    (json.dumps(task, ensure_ascii=False), task_id),
                )
                recovered += 1
            self._connection.commit()
        return recovered

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def _save_upload(upload, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        shutil.copyfileobj(upload.file, output)


def _validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_MODEL_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_MODEL_EXTENSIONS))
        raise ValueError(f"仅支持 3D 模型（{supported}）")
    return suffix


def _run_task(app, task_id: str, source_path: str, preset: str, retopo_method: Optional[str], full: bool = False) -> None:
    store = app.state.task_store
    current = store.get(task_id)
    if not current or current.get("status") == "cancelled":
        return
    store.update(task_id, status="running", progress=5, stage="pipeline")
    try:
        runner = run_full_model_pipeline if full else run_model_pipeline
        result = runner(
            source_path,
            str(app.state.output_dir / "tasks"),
            app.state.config,
            preset,
            retopo_method,
        )
        if store.get(task_id).get("status") != "cancelled":
            store.update(task_id, status=result["status"], progress=100, stage="completed", result=result, error=None)
    except Exception as exc:
        if store.get(task_id).get("status") != "cancelled":
            store.update(task_id, status="failed", stage="failed", error=str(exc))


def create_app(config: Optional[Config] = None):
    """创建可运行的 FastAPI 应用实例。"""
    try:
        from fastapi import FastAPI, File, Form, HTTPException, UploadFile
        from fastapi.responses import FileResponse
    except ImportError as exc:
        raise RuntimeError("启动 API 需要安装 fastapi、uvicorn 和 python-multipart") from exc

    app = FastAPI(title="TopoFlow API", version="0.1.0")
    app.state.config = config or Config()
    app.state.output_dir = Path(app.state.config.output_dir).expanduser().resolve() / "api"
    app.state.output_dir.mkdir(parents=True, exist_ok=True)
    app.state.task_store = TaskStore(str(app.state.output_dir / "tasks.sqlite3"))
    app.state.task_store.recover_incomplete()
    app.state.task_queue = create_queue_backend(config_to_dict(app.state.config))
    app.state.worker = QueueWorker(
        app.state.task_queue,
        lambda payload, cancel: _run_task(
            app, payload["task_id"], payload["source_path"], payload["preset"],
            payload.get("retopo_method"), payload.get("full", False),
        ),
    )
    app.state.worker.start()
    if hasattr(app, "add_event_handler"):
        app.add_event_handler("shutdown", app.state.worker.stop)
        app.add_event_handler("shutdown", app.state.task_store.close)
    elif hasattr(app.router, "add_event_handler"):
        app.router.add_event_handler("shutdown", app.state.worker.stop)
        app.router.add_event_handler("shutdown", app.state.task_store.close)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "topoflow"}

    @app.get("/api/v1/presets")
    def presets():
        return {"presets": PRESETS}

    @app.post("/api/v1/tasks", status_code=202)
    def submit_task(
        file: UploadFile = File(...),
        preset: str = Form("tuanjie_urp"),
        retopo_method: Optional[str] = Form(None),
        full: bool = Form(False),
    ):
        try:
            suffix = _validate_extension(file.filename or "")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if preset not in PRESETS:
            raise HTTPException(status_code=400, detail=f"未知预设: {preset}")

        task_id = uuid.uuid4().hex
        source = app.state.output_dir / "uploads" / task_id / f"source{suffix}"
        _save_upload(file, source)
        task = app.state.task_store.create(
            task_id,
            {"filename": file.filename, "preset": preset, "full": full, "progress": 0, "stage": "queued", "result": None, "error": None},
        )
        app.state.task_queue.push({
            "task_id": task_id, "source_path": str(source), "preset": preset,
            "retopo_method": retopo_method, "full": full,
        })
        return task

    @app.get("/api/v1/tasks/{task_id}")
    def task_status(task_id: str):
        task = app.state.task_store.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return task

    @app.get("/api/v1/tasks")
    def list_tasks(limit: int = 100):
        return {"tasks": app.state.task_store.list(limit)}

    @app.post("/api/v1/tasks/{task_id}/cancel")
    def cancel_task(task_id: str):
        try:
            app.state.worker.cancel(task_id)
            return app.state.task_store.cancel(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="任务不存在") from exc

    @app.get("/api/v1/tasks/{task_id}/result")
    def task_result(task_id: str):
        task = app.state.task_store.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        result = task.get("result") or {}
        report_path = result.get("report_path")
        if not report_path or not Path(report_path).is_file():
            raise HTTPException(status_code=409, detail="任务结果尚不可下载")
        return FileResponse(report_path, filename=f"{task_id}_report.json", media_type="application/json")

    @app.post("/api/v1/validate")
    def validate(file: UploadFile = File(...)):
        try:
            suffix = _validate_extension(file.filename or "")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        validation_id = uuid.uuid4().hex
        work_dir = app.state.output_dir / "validation" / validation_id
        source = work_dir / f"source{suffix}"
        report_path = work_dir / "report.json"
        _save_upload(file, source)
        try:
            return inspect_model(str(source), str(report_path), app.state.config)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


def start_server(host: str = "127.0.0.1", port: int = 8080, config: Optional[Config] = None):
    """启动 Uvicorn API 服务。"""
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("启动 API 需要安装 uvicorn") from exc
    uvicorn.run(create_app(config), host=host, port=port)

# TopoFlow

当前版本：`0.9.0-alpha`。默认目标为团结引擎 URP，UV 后端为 Blender Native。

用户手册：`docs/User_Guide.md`；故障排查：`docs/Troubleshooting.md`；验收报告：`docs/Acceptance_Report_2026-07-26.md`。

> 输入一张角色设计图，自动生成并优化为可直接导入 UE5/Unity 的工业标准 3D 资产。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Web UI
python src/main.py

# CLI 快速闭环（Stage 1/3/4/9）
python src/main.py run --input model.obj --output ./asset

# CLI 完整闭环（Stage 1-9，需要 Blender）
python src/main.py run --full --input model.obj --output ./asset

# 设计图 → 3D → 完整闭环（需要 Meshy API Key）
python src/main.py generate --input design.png --output ./asset

# 启动 API 服务
python src/main.py serve --port 8080

# 仅执行当前已实现的 Stage 1 + Gate A 质检
# 退出码 0=通过，2=质量未通过，1=执行错误
python src/main.py inspect --model model.obj --output inspect_report.json
```

## 项目结构

```
src/
├── main.py                 # 入口（CLI / API / WebUI）
├── config.py               # 配置加载
├── pipeline/
│   ├── graph.py            # LangGraph 状态图
│   ├── state.py            # 状态定义
│   ├── router.py           # 条件路由
│   ├── stage0_generate.py  # 设计图 → 脏模型
│   ├── stage1_diagnose.py  # 预处理与诊断
│   ├── stage2_confirm.py   # 用户确认策略
│   ├── stage3_retopo.py    # 重拓扑
│   ├── stage4_gate_a.py    # 拓扑质检 + TopoStrain + TopoVision
│   ├── stage5_uv.py        # UV 展开与打包
│   ├── stage6_gate_b.py    # UV 质检
│   └── stage10_engine_validate.py # 团结引擎 Gate D 导入验收
│   ├── stage7_bake.py      # 烘焙贴图
│   ├── stage8_gate_c.py    # 烘焙质检
│   └── stage9_pack.py      # 最终打包与报告
├── qc/
│   ├── topostrain.py       # TopoStrain 算法
│   └── topovision.py       # TopoVision 热力图
├── api/
│   └── server.py           # FastAPI 服务
├── agents/
│   └── llm_client.py       # LLM 客户端
├── knowledge/
│   └── chroma_store.py     # ChromaDB 知识库
└── ui/
    └── webui.py            # Gradio 界面
```

## 核心创新

- **TopoStrain**: 基于 cotangent Laplacian 曲率分析的变形质量预测算法
- **TopoVision**: 拓扑健康热力图可视化
- **Style-Aware Topology**: 根据艺术风格自动匹配合适的拓扑策略
- **Adaptive Standards**: 从历史成功/失败中学习的质检知识库
- **REST API**: 可集成至运营平台、CI/CD、测试平台

## 技术栈

LangGraph · GPT-4o · trimesh · Blender (bpy) · QuadRemesher · ChromaDB · FastAPI · Gradio · Redis (可选) · Go (可选)

## 当前完成度

- **已有模型完整链路已接通**：诊断 → 策略确认 → 重拓扑 → Gate A → Blender UV → Gate B → Blender 烘焙 → Gate C → 引擎资产包 → 团结引擎 Gate D。
- **真实质检**：Gate A 保留 OBJ 原始多边形统计；Gate B 分析 UV 覆盖、越界、退化与拉伸；Gate C 检查贴图分辨率、法线与 AO 像素指标。
- **运行入口**：CLI、FastAPI、Gradio Web UI、Watch 文件夹监控和仅质检模式均可运行。
- **基础设施**：文件缓存、SQLite 任务状态、内存/Redis 队列、ChromaDB/JSONL 知识库均已实现。
- **Stage 0 架构已完成**：配置 Meshy Key 后可执行设计图生成 GLB 并进入完整管线；未提供 Key 时会在网络调用前安全报错。
- **外部工具**：已自动定位本机 Blender 4.5.3（`E:/blender/blender.exe`）；Instant Meshes 和 QuadRemesher 保持可选适配。
- 资产是否合格始终以 `report.json` 中三个 Gate 的 `passed` 字段为准。

## 测试

```powershell
$env:PYTHONIOENCODING='utf-8'
python test_mvp_pipeline.py
python test_stage3.py
python test_topostrain.py
```

完整测试依赖 `pytest>=8.0`；涉及 LLM 的测试只有配置 API Key 后才运行。

## REST API

启动服务：

```powershell
python src/main.py --config config.toml serve --host 127.0.0.1 --port 8080
```

当前端点：

- `GET /health`：健康检查。
- `GET /api/v1/presets`：获取引擎预设。
- `POST /api/v1/tasks`：上传已有 3D 模型，后台执行 MVP 管线。
- `GET /api/v1/tasks/{task_id}`：查询任务状态。
- `GET /api/v1/tasks/{task_id}/result`：下载任务 JSON 报告。
- `POST /api/v1/validate`：上传模型并同步执行 Stage 1 + Gate A。

API 本身不要求外部模型 Key。没有 Key 时 Stage 1 使用规则策略；配置 DeepSeek/OpenAI/Anthropic Key 后可启用对应智能策略。任务状态保存在 SQLite 中，服务重启时会把未完成任务标记为 `interrupted`；Redis 队列后端也已实现，可通过配置启用。

## Web UI

直接运行以下命令会在本机 `127.0.0.1:7860` 启动 Gradio：

```powershell
python src/main.py --config config.toml
```

界面包含“运行管线”和“仅质检”两个页面，可勾选完整 Stage 1-9，支持上传 OBJ/PLY/STL/GLB/GLTF、选择引擎预设与重拓扑后端、查看 JSON 报告并下载结果。没有 API Key 时使用规则策略；配置 Key 后自动启用已有 LLM 策略。

## Watch 模式

持续监控目录中的新增或发生变化的模型：

```powershell
python src/main.py --config config.toml watch --folder .\incoming
```

- 支持 OBJ/PLY/STL/GLB/GLTF。
- 首次启动会处理目录中已有的支持文件。
- 使用文件大小和修改时间去重，不会重复处理未变化文件。
- 失败文件会记录错误，只有文件发生变化后才重试，避免无限失败循环。
- 状态保存在 `<output_dir>/watch/watch_state.json`。
- 按 `Ctrl+C` 安全停止。

## 配置要点

`config.toml.example` 包含全部默认配置：

- `[tools].blender_path`：Blender 可执行文件；留空时自动发现。
- `[tools].tuanjie_path`：团结编辑器可执行文件；当前验证版本为 `2022.3.62t11`。
- `[tools].tuanjie_project_dir`：Gate D 使用的团结引擎验证项目目录。
- `[api_keys].meshy`：Stage 0 图生 3D；只有执行 `generate` 时需要。
- `[api_keys].deepseek/openai/anthropic`：可选 LLM 策略；无 Key 时使用规则策略。
- `[standards.gate_a_topology].max_topostrain_score`：按资产类型调整 TopoStrain 上限。
- `[standards.gate_b_uv]`：UV 利用率和拉伸阈值。
- `[knowledge].enabled`：启用成功/失败案例学习。
- `[redis].queue_enabled`：启用 Redis 队列后端。

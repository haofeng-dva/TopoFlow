# TopoFlow

> 输入一张角色设计图，自动生成并优化为可直接导入 UE5/Unity 的工业标准 3D 资产。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Web UI
python src/main.py

# CLI 最小真实闭环（已有 3D 模型）
python src/main.py run --input model.obj --output ./asset

# 启动 API 服务
python src/main.py serve --port 8080

# 仅质检
python src/main.py inspect --model model.obj
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

- 已接通：已有模型 → 诊断 → PyMeshLab 重拓扑/简化 → Gate A → TopoStrain/TopoVision → 审计包。
- 实验性：Instant Meshes、Blender Remesh、QuadRemesher 后端。
- 计划中：设计图生成 3D、UV、贴图烘焙、Gate B/C、Web UI、REST API。
- CLI 成功执行不代表资产通过 Gate A；请以输出 `report.json` 的 `quality_reports.gate_a_topology.passed` 为准。

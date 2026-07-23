# TopoFlow — 独立 Agent 管线产品设计文档 v3.0

> **定位**：从设计图到引擎就绪资产的工业级全自动管线 Agent  
> **形态**：独立本地服务，Web UI + CLI + REST API，零 DCC 软件依赖  
> **一句话**：输入一张角色设计图，自动生成并优化为可直接导入 UE5/Unity 的工业标准 3D 资产  
> **核心创新**：Style-Aware Topology（风格感知拓扑）、TopoStrain（变形质量预测）、TopoVision（拓扑热力图可视化）、Adaptive Standards（自适应质检知识库）、REST API（可集成后端服务）

---

## 目录

1. [产品定义与核心价值](#1-产品定义与核心价值)
2. [目标用户与使用场景](#2-目标用户与使用场景)
3. [完整系统架构](#3-完整系统架构)
4. [全流程工作流（10 步）](#4-全流程工作流10-步)
5. [Agent 智能决策节点](#5-agent-智能决策节点)
6. [命名规范与目录结构](#6-命名规范与目录结构)
7. [任务调度与并发模型](#7-任务调度与并发模型)
8. [缓存策略](#8-缓存策略)
9. [跨软件兼容性设计](#9-跨软件兼容性设计)
10. [Engine Preset 系统](#10-engine-preset-系统)
11. [工业标准知识库](#11-工业标准知识库)
12. [REST API 设计](#12-rest-api-设计)
13. [技术栈与工具清单](#13-技术栈与工具清单)
14. [交付物与成功标准](#14-交付物与成功标准)
15. [附录：运行模式说明](#15-附录运行模式说明)

---

## 1. 产品定义与核心价值

### 1.1 产品名称

**TopoFlow**

### 1.2 解决的核心痛点

| # | 痛点 | TopoFlow 方案 |
|---|------|--------------|
| 1 | AI 生成模型的拓扑混乱、无法直接投入生产 | 全自动重拓扑 + UV 展开 + 贴图烘焙 + **三重工业质检** |
| 2 | 手动处理流程耗时且需要多软件切换 | 一站式管线，从设计图到引擎资产一键完成，后台静默运行 |
| 3 | 缺乏可量化的工业标准来校验资产质量 | 内置可配置的量化规则与知识库，确保每一次交付合规 |

### 1.3 核心价值主张

```
输入          管线（全自动）                    输出
 ┌─────┐    ┌──────────────────────┐    ┌──────────────┐
 │ 设计图 │──▶ 重拓扑/UV/烘焙/质检 │──▶ │ 引擎就绪资产 │
 └─────┘    │ 三重 Gate 审计        │    │ FBX / GLB    │
            │ LLM 智能决策 + 自愈   │    │ 法线/AO/曲率  │
            └──────────────────────┘    └──────────────┘
           ⌛ 端到端 ≤ 20 min/个       📦 直接拖入 UE5/Unity
```

---

## 2. 目标用户与使用场景

| 用户画像 | 场景 | 痛点 | TopoFlow 价值 |
|---------|------|------|--------------|
| **独立开发者** | 用 AI 生成角色概念，需要快速转 3D 原型放进游戏 | 不会用 Maya/Max，花钱外包太贵 | 一键出资产，零 DCC 门槛 |
| **中小游戏团队** | 批量生产风格化角色资产，追求效率 | 流程割裂，人力瓶颈 | 标准化管线，并行任务，稳定交付 |
| **概念设计师** | 验证设计在 3D 空间的效果 | 自己不会建模，等外包周期长 | 快速 3D 化，辅助设计迭代 |
| **求职作品集** | 展示从 2D 到 3D 的完整管线能力 | 缺少工业化作品展示 | 产出可直接运行的引擎资产，含质检报告 |

---

## 3. 完整系统架构

### 3.1 架构总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                        TopoFlow Agent 主控                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │                     Agent 大脑 (LLM)                         │       │
│  │  • 图像分析 → 模型生成参数 JSON                              │       │
│  │  • 诊断分析 → 处理策略 JSON                                  │       │
│  │  • 质检失败分析 → 修复参数                                   │       │
│  │  • 用户偏好学习 → 知识库                                     │       │
│  └────────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  任务规划器     │  │  状态管理器    │  │  工业标准知识库           │   │
│  │  (LLM+规则引擎) │  │  会话记录     │  │  ChromaDB + 规则集       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  任务调度器    │  │  缓存管理器   │  │  运行模式控制器           │   │
│  │  (Queue+Pool) │  │  (Hash-based)│  │  auto_pilot on/off       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │                    交互接口                                  │       │
│  │  Web UI (Gradio)  │  CLI (Argparse)  │  Watch Folder       │       │
│  │  REST API (FastAPI)                                           │       │
│  └────────────────────────────────────────────────────────────┘       │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ 调度 & 状态回调
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       工具执行层（本地环境）                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │  Stage 0: 设计图 → 脏模型                                    │       │
│  │  ┌──────────┐  ┌───────────┐  ┌─────────────────────────┐  │       │
│  │  │ LLM 分析  │─▶│ API 调用   │─▶│ 模型校验 & 下载          │  │       │
│  │  │ prompt 生成│  │ Meshy/    │  │ 完整性检查 + 面数校验    │  │       │
│  │  │ 参数规划  │  │ TripoSR   │  │ 失败 → 重试/切换         │  │       │
│  │  └──────────┘  └───────────┘  └─────────────────────────┘  │       │
│  └────────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │  Stage 1-4: 预处理 / 策略 / 重拓扑 / 拓扑质检 Gate A         │       │
│  │  • trimesh 诊断分析 + 语义区域标记                            │       │
│  │  • QuadRemesher CLI / Instant Meshes 重拓扑                  │       │
│  │  • 自研拓扑审计：三角面占比 / 极点分布 / 面密度方差 / TopoStrain  │       │
│  └────────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │  Stage 5-9: UV / 烘焙 / 打包                                │       │
│  │  • Blender 无头脚本（bpy）自动展开接缝                        │       │
│  │  • UVPackmaster 紧密打包                                     │       │
│  │  • Cycles 烘焙：法线 / AO / 曲率                              │       │
│  │  • UV / 烘焙 / 最终打包 + 报告生成                            │       │
│  │  • 三重质检 Gate B / C                                       │       │
│  └────────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │  兜底 / 容错层                                                 │       │
│  │  • 每阶段超时熔断     • 资源清理 GC                            │       │
│  │  • 异常链路日志快照   • 崩溃自动重启 Worker                    │       │
│  └────────────────────────────────────────────────────────────┘       │
│                                                                      │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ 文件交换
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         资产输出目录                                   │
│                                                                      │
│  {task_id}/                                                          │
│  ├── _high/         脏模 / 高模                                       │
│  ├── _low/          低模（含 UV）                                     │
│  ├── _maps/         贴图套件                                          │
│  ├── _engine/       引擎就绪包                                       │
│  └── report.json    全流程审计日志 + 质检报告                          │
│                                                                      │
│  ▲ 上游：设计图 / AI 模型文件 / ZBrush OBJ                             │
│  ▼ 下游：3ds Max, Maya, UE5, Unity, Substance Painter                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Agent 独立运行原则

- 不依赖任何 DCC 软件（3ds Max / Maya / Blender GUI / ZBrush）
- Blender 以无头模式（bpy）调用，仅作为计算引擎
- 所有交互通过文件系统、Web UI、CLI、REST API 完成
- 支持 **Watch Folder 模式**：指定文件夹内有新图自动触发管线
- 支持 **API Server 模式**：FastAPI 提供异步任务提交/状态轮询/结果下载/webhook 回调，可集成至其他系统

### 3.3 确定性执行保证

> **所有工具调用的实际参数必须通过 JSON Schema 严格校验**  
> **LLM 只输出策略建议，执行层做最后的安全检查**  
> **任何非法参数 → 回退至对应阶段的默认安全参数 → 记录异常日志**

---

## 4. 全流程工作流（10 步）

### 4.1 流程全景图

```
Stage 0           Stage 1            Stage 2            Stage 3
设计图 → 脏模型    预处理 & 诊断      用户确认策略        重拓扑
  │                 │                  │                  │
  ▼                 ▼                  ▼                  ▼
────────→ ────────→ ────────→ ────────→ ────────→
                                  ↑
                            [人工干预点 / Auto-pilot 跳过]

Stage 4            Stage 5            Stage 6            Stage 7
拓扑质检 Gate A    UV 展开 & 打包     UV 质检 Gate B     烘焙贴图
  │                 │                  │                  │
  ▼                 ▼                  ▼                  ▼
────→ ────────→ ────────→ ────────→ ────────→ ────────→
                  ↑                                   ↑
           [失败重试 ≤ 2 次]                    [失败重试 ≤ 2 次]
           [超限 → 暂停报错]                    [超限 → 暂停报错]

Stage 8            Stage 9
烘焙质检 Gate C    最终打包 & 报告
  │                 │
  ▼                 ▼
────→ ────────→ ────────→ ✅ 引擎就绪资产
                  ↑
           [失败重试 ≤ 2 次]
           [超限 → 暂停报错]
```

---

### Stage 0：设计图 → 脏模型（风格化 AI 自动建模）

**输入**：用户上传的设计图（PNG / JPG），支持角色设定、概念图、照片

**过程**：

```
                    ┌─────────────┐
                    │  用户上传设计图 │
                    └──────┬──────┘
                           ▼
                ┌──────────────────────┐
                │ 1. LLM 图像分析       │
                │    • 姿态描述         │
                │    • 体型分类         │
                │    • 风格判定         │
                │    • 对称性检测       │
                │    • 是否需要多视角    │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ 2. 生成 API 参数 JSON  │
                │    Schema 校验通过？    │
                │    否 → 回退默认参数    │
                │    是 → 继续           │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ 3. 缓存命中检查        │
                │    (图像 hash + 参数)  │
                │    命中 → 跳过 API     │
                │    未命中 → 调用 API   │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ 4. API 调用           │
                │    主：Meshy I2D      │
                │    备：TripoSR        │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ 5. 完整性校验          │
                │    • 非空模型          │
                │    • 面数在合理范围     │
                │    • 可通过 trimesh 加载 │
                │    失败 → 重试/切换    │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ 输出: stage0_raw.obj  │
                └──────────────────────┘
```

**参数 JSON Schema 示例**：

```json
{
  "type": "object",
  "required": ["pose", "body_type", "style", "symmetric"],
  "properties": {
    "pose": { "type": "string", "minLength": 5, "description": "姿态描述，如'A字站立双手自然下垂'" },
    "body_type": { "type": "string", "enum": ["normal", "slim", "muscular", "chibi"] },
    "style": { "type": "string", "enum": ["stylized", "pbr", "toon", "realistic"] },
    "symmetric": { "type": "boolean" },
    "multi_view_hint": { "type": "string", "description": "多视角补充提示，可选" }
  }
}
```

**失败处理策略**：

| 失败类型 | 行为 |
|---------|------|
| API 超时 / 无响应 | 等待 30s 重试 1 次 → 切换备选 API |
| 返回空模型 / 文件损坏 | 重试 1 次（相同 API）→ 切换备选 API |
| 面数超出合理范围 | 记录日志，继续流程（后续质检会处理） |
| LLM 分析返回非法 JSON | 回退至通用默认参数，记录低置信度日志 |

**输出**：`stage0_raw.obj` → 进入 Stage 1

---

### Stage 1：预处理与诊断

**预处理**：

| 操作 | 工具 | 说明 |
|------|------|------|
| 合并顶点 | pymeshlab | 消除重复顶点 |
| 法线统一 | pymeshlab | 确保法线方向一致性 |
| 修复非流形 | pymeshlab / trimesh | 修复边界边、非流形顶点 |
| 归一化尺寸 | trimesh | 可选，将模型缩放至单位立方体或指定高度 |
| 格式标准化 | trimesh | 统一为内部 Mesh 表示 |

**诊断分析**：

```
┌─────────────────────────────────────────────────────────┐
│                    诊断报告                              │
├─────────────────────────────────────────────────────────┤
│  面数统计：                                              │
│    • 总三角面数：123456                                   │
│    • 三角形占比：98.7%                                    │
│    • 四边形占比：1.2%                                     │
│    • N-gon 占比：0.1%                                    │
│  拓扑质量：                                              │
│    • 非流形边数：3                                        │
│    • 边界边数：12                                        │
│    • 水密性：是 / 否                                     │
│  特征曲率：                                              │
│    • 高曲率区域占比：15%                                   │
│    • 平面区域占比：45%                                    │
│  语义区域（轻量分割）：                                    │
│    • 头部 / 躯干 / 四肢 / 关节标记                         │
│  尺寸：                                                  │
│    • 包围盒：1.2m x 0.5m x 0.3m                           │
└─────────────────────────────────────────────────────────┘
```

**Agent 大脑介入——输出策略 JSON**：

```json
{
  "model_type": "organic",
  "retopo_method": "quadremesher",
  "target_face_count": 8000,
  "uv_resolution": 2048,
  "uv_channels": 1,
  "bake_resolution": 2048,
  "normal_space": "directx",
  "preserve_features": ["face", "hands"],
  "manual_guidance_needed": false,
  "auto_pilot_eligible": true
}
```

**输出**：
- `strategy.json`
- `diagnosis_report.json`
- 进入 Stage 2

---

### Stage 2：用户确认策略（人工干预点 / Auto-pilot 跳过）

**UI 展示内容**：

```
╔══════════════════════════════════════════════════════════╗
║                 处理策略预览                               ║
╠══════════════════════════════════════════════════════════╣
║  模型类型    : 有机体 (角色)                                ║
║  风格判定    : 风格化卡通 [Style-Aware ✓]                    ║
║  重拓扑方法  : QuadRemesher                                ║
║  目标面数    : 8,000                                       ║
║  UV 分辨率  : 2048                                        ║
║  烘焙分辨率  : 2048                                        ║
║  法线空间    : DirectX (-Y)                                ║
║  语义区域    : 头部 / 躯干 / 四肢 / 关节                     ║
╠══════════════════════════════════════════════════════════╣
║  [ ✅ 一键确认 ]  [ 修改参数 ]  [ 上传引导曲线 ]  [ 取消 ]   ║
╚══════════════════════════════════════════════════════════╝
```

**用户可选操作**：

| 操作 | 说明 |
|------|------|
| 一键确认 | 直接按策略执行，默认行为 |
| 修改参数 | 编辑目标面数、分辨率、法线空间等参数 |
| 上传引导曲线 | 带顶点色标记的 OBJ，指定拓扑流向 |
| 上传冻结遮罩 | 保护特定区域（如手指、面部细节），禁止拓扑修改 |
| 取消 | 终止当前任务 |

**Auto-pilot 模式下的行为**：

- 策略自动通过，跳过 Stage 2
- 仅在质检失败次数耗尽时暂停报错，等待用户介入
- 配置文件通过 `config.toml` 的 `[run_mode] auto_pilot = true` 控制

**输出**：用户确定的执行策略（或自动通过的原始策略）

---

### Stage 3：重拓扑

**执行流程**：

```
┌──────────────────┐
│ 策略 JSON         │
│ 引导曲线 (可选)    │
│ 冻结遮罩 (可选)    │
└────────┬─────────┘
         ▼
┌──────────────────────────────────┐
│ 选择重拓扑引擎                    │
│                                  │
│ 有机体/角色 → QuadRemesher CLI   │
│   → 参数：目标面数 / 对称性 /     │
│     自适应曲率保留 / 引导曲线      │
│                                  │
│ 硬表面 → 基于平面检测的分块重拓扑   │
│   → 平面检测 → 各平面独立重拓扑    │
│   → 合并结果 → 边界对齐           │
│                                  │
│ 备选 → Instant Meshes            │
└────────┬─────────────────────────┘
         ▼
┌──────────────────┐
│ 输出: stage3_low.obj │
└──────────────────┘
```

**QuadRemesher 参数说明**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `target_face_count` | 策略指定 | 目标面数，受 style_profile 影响 |
| `adaptivity` | 1.0 | 曲率自适应保留，值越高越保留细节 |
| `symmetry` | true | 对称性约束 |
| `hard_edge_angle` | 60° | 硬边保留角度阈值 |
| `guide_curve_file` | 可选 | 引导曲线 OBJ 路径 |
| `freeze_mask_file` | 可选 | 冻结遮罩 OBJ 路径 |

**Style-Aware 参数映射**：Stage 1 判定的 `style_profile` 自动决定重拓扑的核心参数：

| Style Profile | 目标面数 | adaptivity | 拓扑策略说明 |
|---------------|---------|-----------|------------|
| `stylized_cartoon` | 6,000 - 8,000 | 0.7 | 简化边缘环路，关节区域适度稀疏，允许 3-5% 三角面 |
| `semi_realistic` | 10,000 - 15,000 | 1.0 | 严格四边面，面部/手部独立环路，关节高密度 |
| `pbr_realistic` | 15,000 - 25,000 | 1.2 | 最高精度，全部四边面，解剖学环路引导 |
| `toon_anime` | 4,000 - 6,000 | 0.5 | 极简拓扑，大量允许三角面，无严格环路要求 |

> 风格化卡通和二次元风格使用更低面数和更宽松的拓扑标准，因为其渲染方式（平涂/卡通材质）对变形精度的要求低于 PBR 写实。这在不影响最终视觉质量的前提下大幅减少了计算开销。

**输出**：`stage3_low.obj`

---

### Stage 4：拓扑质检 Gate A

**审计规则（默认 UE5 工业标准）**：

| 指标 | 合格标准 | 说明 |
|------|---------|------|
| 三角面占比 | ≤ 5% | 四边面为主，极小三角面可接受 |
| 极点分布 | 变形区域禁止 | 面部、关节等关键区域不允许非 4 价顶点 |
| 面密度方差 | ≤ 30% | 大面与极密小面之间的差异不能过大 |
| 边界边 | 0 | 模型必须是水密流形 |
| 循环边完整性 | 可选 | 角色眼/口循环边完整 |

**TopoStrain — 变形质量预测（算法创新）**：

第四项审计指标，也是核心算法创新。传统拓扑质检只检查几何规范性（三角面占比、价数），无法预测拓扑在动画变形时的表现。TopoStrain 直接度量边缘环路方向与表面曲率方向的偏离程度，偏离大的区域在动画时会产生 pinch / 走样。

**算法核心**：

```python
def topostrain_score(mesh):
    # Step 1: cotangent Laplacian → 逐顶点曲率估计
    L = cotangent_laplacian(mesh.vertices, mesh.faces)
    curvature_normals = L @ mesh.vertices
    
    # Step 2: PCA 分析一环邻域 → 局部拓扑流向
    flow_directions = []
    for v in mesh.vertices:
        local = mesh.vertices[mesh.vertex_neighbors[v]]
        _, _, vh = np.linalg.svd(local - local.mean(axis=0))
        flow_directions.append(vh[0])
    
    # Step 3: 计算偏离角 → 标记变形风险
    angles = arccos(clip(abs(dot(curvature_normals, flow_directions)), 0, 1))
    risk_mask = angles > threshold  # ≥ 30° 为高风险
    
    # Step 4: 全局评分 (0=完美, 100=极差)
    global_score = 100 * (1 - mean(sigmoid(angles - threshold)))
    return risk_mask, global_score
```

**质检标准**：

| TopoStrain 评分 | 判定 |
|----------------|------|
| 0 - 20 | 优秀，拓扑高度对齐曲率 |
| 20 - 40 | 合格，可接受 |
| 40 - 60 | 边缘，建议调整后重试 |
| > 60 | 不合格，拓扑流向与曲率严重错位 |

> TopoStrain 是 Gate A 中唯一**具有预测能力**的指标——它不评估拓扑的当前状态，而是预测它在动画变形时会不会出问题。

**TopoVision — 拓扑健康热力图（可视化创新）**：

Gate A 通过后，系统额外生成一张**颜色编码的拓扑质量热力图**：

| 颜色 | 含义 |
|------|------|
| 绿色 | 良好拓扑（低面密度方差、4 价顶点、低 TopoStrain） |
| 黄色 | 可接受（轻微偏离，不影响使用） |
| 红色 | 潜在问题区（极点集中、面密度突变、高 TopoStrain） |

- 热力图以顶点色形式嵌入 OBJ 文件（`stage4_low_heatmap.obj`）
- 同时输出一张 360° 预览图，可在 Web UI 中直接查看
- 用户可直观定位拓扑问题区域，无需逐个顶点检查

**失败处理**：

```
                    ┌─────────┐
                    │ Gate A  │
                    │ 不合格   │
                    └────┬────┘
                         ▼
                ┌──────────────────────┐
                │ LLM 分析失败指标       │
                │ • 三角面占比过高？      │
                │ • 极点分布异常？       │
                │ • 面密度方差过大？      │
                │ • TopoStrain 评分过高？ │
                └────────┬─────────────┘
                         ▼
                ┌──────────────────────┐
                │ 生成调整方案           │
                │ • 提高目标面数         │
                │ • 调整边保留参数       │
                │ • 修改曲率自适应值      │
                │ • 添加引导曲线约束流向  │
                └────────┬─────────────┘
                         ▼
                ┌──────────────────────┐
                │ 重试重拓扑             │
                │ 记录 retry_count      │
                │ retry_count ≤ 2       │
                └────────┬─────────────┘
                         ▼
               ┌────────────────────────┐
               │ 重试 ≥ 3 次？           │
               │ 是 → 生成失败报告        │
               │      暂停等待用户        │
               │ 否 → 返回 Stage 3       │
               └────────────────────────┘
```

**输出**：
- 通过：`stage4_low_passed.obj` + `stage4_low_heatmap.obj`（TopoVision 热力图），进入 Stage 5
- 失败暂停：`gate_a_failure_report.json`（含 TopoStrain 评分）

### Stage 5：UV 展开与打包

**执行流程**：

```
┌──────────────────┐
│ stage4_low_passed.obj │
└────────┬─────────┘
         ▼
┌──────────────────────────────────┐
│ Blender 无头脚本 (bpy)            │
│                                  │
│ 1. 导入低模                       │
│ 2. 标记接缝：                     │
│    • 基于硬边自动检测              │
│    • 基于材质 ID 分组（若有）       │
│    • 语义区域边界（头/身交接缝）    │
│ 3. UV 展开 (Smart UV Project)    │
│ 4. UVPackmaster 紧密打包         │
│    • 岛间距 4px（@2048）          │
│    • 旋转允许                     │
│    • 第一象限约束                  │
│ 5. 如需光照贴图：                  │
│    • 生成第二套 UV                │
│    • 偏移至合法象限                │
└────────┬─────────────────────────┘
         ▼
┌──────────────────┐
│ 输出: stage5_low_uv.fbx │
└──────────────────┘
```

**UVPackmaster 关键参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `tex_resolution` | 2048 | 参考纹理分辨率 |
| `island_margin` | 4 | 岛间距（像素） |
| `allow_rotation` | true | 允许旋转 UV 岛 |
| `fit_to_first_quadrant` | true | 约束至第一象限 |
| `pack_quality` | high | 打包质量 |

**输出**：`stage5_low_uv.fbx`

---

### Stage 6：UV 质检 Gate B

**审计规则**：

| 指标 | 合格标准 | 说明 |
|------|---------|------|
| 岛间距 | ≥ 4px (以 2048 分辨率计) | 防止贴图渗色 |
| 关键区域拉伸 | ≤ 3% | 面部、手部等（若有标记） |
| 第一象限利用率 | ≥ 80% | UV 空间利用率 |
| 意外重叠 | 无 | 检测岛间重叠和岛内翻转 |

**失败处理**：

- LLM 分析失败原因（接缝位置不佳 / 打包参数不合理）
- 自动调整接缝或打包参数重展，最多 2 次
- 超限 → 暂停报错，生成 `gate_b_failure_report.json`

**输出**：
- 通过：模型进入 Stage 7
- 失败暂停：`gate_b_failure_report.json`

---

### Stage 7：烘焙贴图

**执行流程**：

```
┌──────────────────┐
│ 低模 (带 UV, FBX)   │
│ 高模 (stage0_raw)   │
└────────┬─────────┘
         ▼
┌──────────────────────────────────┐
│ Blender 无头 Cycles 烘焙          │
│                                  │
│ 1. 加载低模 + 高模               │
│ 2. Cage 自动生成                  │
│    • 基于低模法线外扩             │
│    • 默认膨胀距离：0.01 (世界单位)  │
│ 3. 烘焙贴图组：                   │
│    ┌────────────────────┐        │
│    │ 法线贴图 (Normal)   │        │
│    │   • 切线空间         │        │
│    │   • DX (-Y) / GL (+Y)│        │
│    ├────────────────────┤        │
│    │ 环境光遮蔽 (AO)     │        │
│    │   • 采样率 256      │        │
│    │   • 分布距离 0.2    │        │
│    ├────────────────────┤        │
│    │ 曲率贴图            │        │
│    ├────────────────────┤        │
│    │ 可选组：             │        │
│    │   • 厚度贴图         │        │
│    │   • 空腔贴图         │        │
│    │   • 材质 ID 贴图    │        │
│    └────────────────────┘        │
│ 4. 输出格式：PNG 16-bit          │
└────────┬─────────────────────────┘
         ▼
┌──────────────────┐
│ 输出贴图套件       │
│ normal_dx.png     │
│ normal_gl.png     │
│ ao.png            │
│ curvature.png     │
│ (optional)         │
└──────────────────┘
```

**输出**：贴图文件套件

---

### Stage 8：烘焙质检 Gate C

**审计规则**：

| 指标 | 合格标准 | 说明 |
|------|---------|------|
| 法线接缝连续性 | 无明显断裂 | 相邻 UV 岛的切空间法线应连续 |
| AO 质量 | 无异常噪点 / 死黑区域 | 直方图分布在 10-240 区间内 |
| 色彩空间正确 | 法线：线性 / AO：sRGB | 元数据检查 |
| 分辨率匹配 | 与配置一致 | 所有贴图分辨率相同 |

**失败处理**：

- LLM 分析失败原因（cage 距离不合理 / 采样率不足 / 高模低模不匹配）
- 自动调整参数重烘，最多 2 次
- 超限 → 暂停报错，生成 `gate_c_failure_report.json`

**输出**：
- 通过：贴图套件进入 Stage 9
- 失败暂停：`gate_c_failure_report.json`

---

### Stage 9：最终打包与报告

**打包内容**：

```
{task_id}_v{version}/
├── _high/                         # 原始高模 / 脏模
│   └── {asset_name}_hires.obj
│
├── _low/                          # 低模（含 UV 和层级命名）
│   ├── {asset_name}_low.fbx
│   └── {asset_name}_low.glb       # 可选
│
├── _maps/                         # 贴图套件
│   ├── {asset_name}_Normal.png    # 默认 DX 切线空间
│   ├── {asset_name}_Normal_GL.png # OpenGL 版本（按配置选）
│   ├── {asset_name}_AmbientOcclusion.png
│   ├── {asset_name}_Curvature.png
│   └── {asset_name}_MaterialID.png # 可选
│
├── _engine/                       # 引擎就绪包
│   └── {asset_name}_package.glb   # 含贴图的完整资产（可选）
│
├── report.json                    # 全流程审计日志 + 质检报告
└── pipeline.log                   # 详细执行日志
```

**report.json 结构**：

```json
{
  "task_id": "topoflow_20260713_001",
  "asset_name": "serpent_goddess",
  "timeline": {
    "stage0_duration_s": 45.2,
    "stage1_duration_s": 12.1,
    "stage3_duration_s": 30.5,
    "stage5_duration_s": 22.8,
    "stage7_duration_s": 60.3,
    "stage9_duration_s": 5.1,
    "total_duration_s": 176.0
  },
  "quality_reports": {
    "gate_a_topology": {
      "passed": true,
      "retry_count": 0,
      "metrics": {
        "triangle_pct": 1.2,
        "pole_count": 8,
        "face_density_variance": 0.18,
        "boundary_edges": 0,
        "topostrain_score": 15.3,
        "style_profile": "stylized_cartoon"
      }
    },
    "gate_b_uv": {
      "passed": true,
      "retry_count": 1,
      "metrics": {
        "island_gap_px": 4.2,
        "first_quadrant_utilization": 0.87,
        "stretch_pct": 2.1,
        "overlap_detected": false
      }
    },
    "gate_c_bake": {
      "passed": true,
      "retry_count": 0,
      "metrics": {
        "normal_seam_continuity": 0.96,
        "ao_noise_level": 0.03,
        "color_space_valid": true
      }
    }
  },
  "config_used": {
    "target_faces": 8000,
    "uv_resolution": 2048,
    "bake_resolution": 2048,
    "normal_space": "directx",
    "auto_pilot": false
  },
  "output_files": [
    "serpent_goddess_low.fbx",
    "serpent_goddess_low.glb",
    "serpent_goddess_low_heatmap.obj",
    "serpent_goddess_Normal.png",
    "serpent_goddess_AmbientOcclusion.png",
    "serpent_goddess_Curvature.png",
    "serpent_goddess_topostrain_report.png"
  ]
}
```

**Agent 收尾**：

1. 将成功参数（模型类型 / 目标面数 / 分辨率 / 重拓扑引擎）记入用户偏好知识库
2. 更新 ChromaDB 中的工业标准匹配记录
3. 清理临时文件（可配置保留策略）

---

## 5. Agent 智能决策节点

### 5.1 决策节点汇总

| 阶段 | 决策点 | 输入 | 输出 | 失败处理 |
|------|--------|------|------|----------|
| Stage 0 | 模型生成策略 | 设计图（LLM 视觉分析） | API 调用参数 JSON | Schema 非法 → 回退默认参数；API 失败 → 重试/切换 |
| Stage 1 | 处理策略规划 | 诊断数据（面数/拓扑/语义） | `strategy.json` | 关键字段缺失 → 默认安全策略 |
| Stage 4 | 拓扑修复决策 | Gate A 失败指标 | 新重拓扑参数 | 自动重试 ≤ 2 次 → 暂停报错 |
| Stage 6 | UV 修复决策 | Gate B 失败指标 | 新 UV 参数 | 自动重试 ≤ 2 次 → 暂停报错 |
| Stage 8 | 烘焙修复决策 | Gate C 失败指标 | 新烘焙参数 | 自动重试 ≤ 2 次 → 暂停报错 |

### 5.2 LLM 输出 Schema 保障

所有 LLM 输出 JSON 必须通过相应 Schema 校验，校验规则：

```
LLM 输出 → JSON Schema 校验 → 通过 → 送入执行层
                              → 失败 → 回退默认参数 + 记录低置信度日志
```

### 5.3 创新技术总览

| 创新 | 类型 | 所在阶段 | 一句话 |
|------|------|---------|--------|
| **Style-Aware Topology** | 系统功能 | Stage 1 / 3 / 10 | LLM 判定输入设计的艺术风格，自动匹配合适的拓扑策略和质检标准 |
| **TopoStrain** | 算法 | Stage 4 Gate A | 基于 cotangent Laplacian 曲率分析的变形质量预测指标，业内目前无公开同类方案 |
| **TopoVision** | 可视化 | Stage 4 输出 | 将拓扑质量指标映射为顶点色热力图，用户可直接看到问题区域 |
| **Adaptive Standards** | 系统功能 | Chapter 11 | ChromaDB 驱动的知识进化系统，质检规则随使用逐渐优化 |

### 5.4 用户偏好学习机制

每次成功后记录：
- 模型类型（organic / hard_surface / prop）
- Style Profile（stylized_cartoon / semi_realistic / pbr_realistic / toon_anime）
- 使用的重拓扑引擎及参数
- 目标面数
- UV / 烘焙分辨率
- 法线空间偏好（DX / GL）
- TopoStrain 评分（用于 baseline 更新）

存储于 ChromaDB，下次同类型模型时优先匹配历史成功参数。

---

## 6. 命名规范与目录结构

### 6.1 资产命名规范

```
{asset_name}_{type}_{variant?}.{ext}

示例：
serpent_goddess_hires.obj       # 高模
serpent_goddess_low.fbx         # 低模（含 UV）
serpent_goddess_low.glb         # 低模（GLTF）
serpent_goddess_Normal.png      # 法线贴图（DX 默认）
serpent_goddess_Normal_GL.png   # 法线贴图（OpenGL）
serpent_goddess_AmbientOcclusion.png  # AO
serpent_goddess_Curvature.png   # 曲率
serpent_goddess_MaterialID.png  # 材质 ID
```

### 6.2 层级命名规范（FBX 内部）

| 层级 | 命名规则 | 示例 |
|------|---------|------|
| Root | `{asset_name}_root` | `serpent_goddess_root` |
| Mesh | `{asset_name}_low_mesh` | `serpent_goddess_low_mesh` |
| Materials | `{asset_name}_mat_{id}` | `serpent_goddess_mat_01` |

### 6.3 UV 通道规范

| 通道 | 用途 | 说明 |
|------|------|------|
| UV0 | 漫反射 / 法线烘焙 | 必选，第一象限 |
| UV1 | 光照贴图 | 可选，偏移至第二象限以避开 UV0 |

### 6.4 贴图分辨率层级

| 档位 | 分辨率 | 适用场景 |
|------|--------|---------|
| 1K | 1024×1024 | 移动端、低面数道具 |
| 2K | 2048×2048 | 默认，风格化角色 |
| 4K | 4096×4096 | 高精度、影视级 |

---

## 7. 任务调度与并发模型

### 7.1 架构

```
┌─────────────────────────────────────────────┐
│             任务调度器 (Task Scheduler)        │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  任务队列  │  │ Worker   │  │ 状态管理  │  │
│  │  (FIFO)   │─▶│ Pool     │  │ 回调     │  │
│  └──────────┘  │ (1~3)    │  └──────────┘  │
│                └──────────┘                 │
│  ┌──────────┐                               │
│  │  优先级   │                               │
│  │  队列     │                               │
│  │  (可选)   │                               │
│  └──────────┘                               │
└─────────────────────────────────────────────┘
```

### 7.2 调度策略

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_workers` | 1 | 同时处理的管线数，受 GPU 显存限制 |
| `queue_order` | FIFO | 先进先出，可选优先级 |
| `worker_timeout` | 3600s | 单 Worker 超时熔断 |
| `retry_queue_delay` | 30s | 失败重试的入队延迟 |

### 7.3 队列后端

当前实现使用 Python 内存队列（`queue.Queue`），可选切换至 Redis：

| 方案 | 优势 | 劣势 |
|------|------|------|
| 内存队列（默认） | 零依赖，开箱即用 | 任务丢失风险（进程退出），不支持跨进程 |
| Redis（可选） | 持久化、支持多 Worker 跨进程、可做任务优先级 | 多一个依赖，部署复杂度略增 |

切换到 Redis 时，Task Scheduler 的接口保持不变——通过抽象队列接口 `QueueBackend` 切换实现。

```python
class QueueBackend:
    def push(self, task: dict): ...
    def pop(self) -> dict | None: ...
    def ack(self, task_id: str): ...
    def nack(self, task_id: str): ...

class MemoryQueue(QueueBackend): ...    # 默认
class RedisQueue(QueueBackend):  ...    # 可选
```

### 7.4 资源竞争管理

- Blender 无头模式单实例占用 GPU 显存约 1-2GB（@ 2K 烘焙）
- 默认 1 Worker，避免显存竞争
- 多 GPU 时可启用多 Worker 并行
- 任务开始前检查系统资源（内存 / 显存 / 磁盘），不足时排队等待

---

## 8. 缓存策略

### 8.1 缓存层级

```
Cache Key = SHA256(设计图内容 + 参数 JSON)

Stage 0 缓存 → raw_mesh
Stage 3 缓存 → retopo_mesh (key 含重拓扑参数)
Stage 5 缓存 → uv_mesh (key 含 UV 参数)
Stage 7 缓存 → bake_maps (key 含烘焙参数)
```

### 8.2 缓存行为

| 缓存 | 命中条件 | 效果 |
|------|---------|------|
| Stage 0 | 同一设计图 + 同一生成参数 | 跳过 API 调用，直接复用脏模 |
| Stage 3 | 同一脏模 + 同一重拓扑参数 | 跳过重拓扑，直接复用低模 |
| Stage 5 | 同一低模 + 同一 UV 参数 | 跳过 UV 展开 |
| Stage 7 | 同一低模 + 同一高模 + 同一烘焙参数 | 跳过烘焙 |

### 8.3 缓存后端

| 方案 | 说明 |
|------|------|
| 文件缓存（默认） | 以文件 hash 为 key，存储至 `{output_dir}/.cache/`，LRU 淘汰 |
| Redis（可选） | 切换为 Redis 缓存，支持自动过期（TTL）、跨 Worker 共享、分布式部署 |

### 8.4 缓存管理

- 默认缓存目录：`{output_dir}/.cache/`（文件缓存模式）
- 过期策略：LRU，最大 20 项（可配置）
- Redis TTL：默认 24 小时（可配置）
- 手动清除：`topoflow cache clear` / Web UI 一键清除

---

## 9. 跨软件兼容性设计

### 9.1 上下游生态

| 上游 / 下游 | 交互方式 | 说明 |
|-----------|----------|------|
| **上游：设计图** | 用户直接上传或拖拽 | 无需任何 DCC 软件 |
| **上游：ZBrush 等雕刻** | 用户将 OBJ/FBX 放入监控文件夹，直接从 Stage 1 开始 | 跳过 Stage 0，仅做重拓扑/UV/烘焙优化 |
| **上游：Meshy / Luma / TripoSR** | 自动调用 API 作为 Stage 0 实现 | 亦可手动下载模型放入输入文件夹 |
| **下游：3ds Max / Maya** | 输出标准 FBX，带命名规范 | 可直接导入绑定 / 编辑 |
| **下游：Unreal Engine 5** | 输出 GLB 或 FBX，符合 Nanite 要求 | 贴图命名后缀自动识别，法线 DX 空间 |
| **下游：Unity** | 同上，法线格式可切换为 OpenGL | `config.toml` 中配置法线空间 |
| **下游：Substance Painter** | 输出低模 FBX + 法线/AO/曲率贴图 | 可直接新建项目继续绘制材质 |

### 9.2 法线空间切换

| 目标引擎 | 法线空间 | 贴图后缀 |
|---------|---------|---------|
| UE5 | DirectX (-Y) | `_Normal.png` |
| Unity | OpenGL (+Y) | `_Normal_GL.png` |
| 通用 | 可配置 | 按配置选择 |

### 9.3 FBX 导出设置

| 设置 | 值 |
|------|-----|
| 坐标轴 | Y-Up (UE5/Unity 通用) |
| 单位 | 厘米 (cm) |
| 嵌入贴图 | 否（使用相对路径引用） |
| 平滑组 | 自动，基于硬边角度 |
| 材质 | 标准 Blender BSDF（命名规范） |

---

## 10. Engine Preset 系统

### 10.1 设计目标

让用户通过**一个下拉切换**改变整条管线的输出标准，无需手动修改每一项参数。

切换 Preset 时自动更新以下参数集：

| 参数域 | 受影响的配置项 |
|--------|--------------|
| **重拓扑** | 目标面数、面密度方差阈值、极点容忍度 |
| **UV** | 分辨率、岛间距、第一象限利用率要求 |
| **烘焙** | 贴图分辨率、法线空间（DX/GL）、采样率 |
| **质检** | Gate A/B/C 全部阈值 |
| **输出** | 贴图格式、GLB 可选、后缀命名 |

### 10.2 预设定义

```toml
[presets.ue5_nanite]
label = "UE5 Nanite（默认）"
face_budget = 12000          # 风格化角色推荐面数
face_density_variance = 0.30
max_triangle_pct = 5.0
uv_resolution = 2048
bake_resolution = 2048
normal_space = "directx"     # UE5 要求 -Y
uv_island_gap_px = 4
uv_first_quadrant_util = 0.80
normal_color_space = "linear"
ao_color_space = "srgb"
require_watertight = true
output_glb = true
output_normal_gl = false

[presets.unity]
label = "Unity 标准"
face_budget = 10000
face_density_variance = 0.30
max_triangle_pct = 7.0       # Unity 对四边面容忍度稍高
uv_resolution = 2048
bake_resolution = 2048
normal_space = "opengl"      # Unity 要求 +Y
uv_island_gap_px = 4
uv_first_quadrant_util = 0.80
normal_color_space = "linear"
ao_color_space = "srgb"
require_watertight = true
output_glb = true
output_normal_gl = true      # 额外输出 GL 法线

[presets.mobile]
label = "移动端优化"
face_budget = 5000           # 低面数
face_density_variance = 0.35 # 移动端对面密均衡要求略低
max_triangle_pct = 10.0      # 移动端适度容忍三角面
uv_resolution = 1024         # 低分辨率
bake_resolution = 1024
normal_space = "directx"
uv_island_gap_px = 2         # 小纹理下岛间距放宽
uv_first_quadrant_util = 0.75
normal_color_space = "linear"
ao_color_space = "srgb"
require_watertight = false   # 移动端特定场景可不水密
output_glb = true
output_normal_gl = false

[presets.custom]
label = "自定义"
# 空预设，完全由用户自由配置

[presets.ue5_nanite.stylized_cartoon]
label = "风格化卡通"
face_budget = 7000
max_triangle_pct = 8.0
 face_density_variance = 0.35

[presets.ue5_nanite.semi_realistic]
label = "半写实"
face_budget = 12000
max_triangle_pct = 3.0
face_density_variance = 0.25

[presets.ue5_nanite.pbr_realistic]
label = "PBR 写实"
face_budget = 20000
max_triangle_pct = 1.0
face_density_variance = 0.20
```

**每个预设内部按 Style Profile 细分**。以 UE5 Nanite 预设为例，选择「风格化卡通」子配置时管线自动使用更低面数（7,000 vs 12,000）和更宽松的拓扑标准（允许 8% 三角面），因为风格化角色的渲染方式对拓扑精度的要求低于写实角色。

> **为什么强调风格化**：独立游戏和中小团队的产品大多使用风格化/卡通美术风格。TopoFlow 的 Style-Aware 机制确保：一个卡通角色不会因为拓扑不够精细而被过度处理（造成不必要的面数浪费），也不会因为使用了写实标准的质检而误判为不合格。对于风格化作品集制作，这套机制意味着：你可以在 5 分钟内从设计图拿到一个拓扑干净、UV 正确、贴图就绪的卡通角色。

**Web UI 交互**：

```
┌──────────────────────────────────────┐
│  Engine Preset: [UE5 Nanite     ▼]   │
│  Style Profile: [风格化卡通     ▼]   │
│                  风格化卡通            │
│                  半写实               │
│                  PBR 写实             │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  当前预设参数摘要                      │
│  ┌──────────┬─────────────────────┐  │
│  │ 目标面数   │ 12,000              │  │
│  │ UV 分辨率 │ 2048                │  │
│  │ 法线空间  │ DirectX (-Y)        │  │
│  │ 烘焙分辨率│ 2048                │  │
│  └──────────┴─────────────────────┘  │
└──────────────────────────────────────┘
```

切换 Preset 后 Web UI 中的参数面板自动刷新为对应值，用户可在当前预设基础上再做微调（若选择「自定义」则完全自由配置）

## 11. 工业标准知识库

### 11.1 知识库结构

- **存储**：ChromaDB（向量数据库）
- **索引字段**：模型类型 / 面数范围 / 风格 / 引擎目标
- **存储内容**：
  - 历史成功参数组合
  - 工业标准规则（拓扑/UV/贴图）
  - 各引擎官方最佳实践摘录
  - 常见失败案例及解决方案

### 11.2 硬编码规则集（默认）

| 规则 | 值 | 来源 |
|------|-----|------|
| 四边面占比 | ≥ 95% | 通用绑定/蒙皮标准 |
| 三角面占比 | ≤ 5% | 引擎行业惯例 |
| UV 岛间距 | ≥ 4px (@2K) | 防止贴图渗色 |
| UV 第一象限利用率 | ≥ 80% | 纹理空间最大化 |
| 法线贴图格式 | 切线空间 | UE5 / Unity 通用 |
| 面密度方差 | ≤ 30% | 变形一致性要求 |
| 角色面积 | 8K-15K 三角面（风格化） | 移动/PC 中档角色 |
| 模型水密性 | 必须 | 烘焙/引擎通用要求 |

### 11.3 Adaptive Standards — 自适应质检知识库（系统创新）

**核心思想**：质检规则不是一成不变的。每次成功或失败的案例都被存入知识库，系统从中学习，逐渐优化自己的决策。

**工作机制**：

```
每次任务完成后:
  ┌────────────────────────────────────────────┐
  │ 记录 {输入特征 + 策略参数 + 质检结果} 到    │
  │ ChromaDB                                    │
  │    • 输入特征: style_profile, model_type,   │
  │      面数范围, 语义区域                       │
  │    • 策略参数: 重拓扑/UV/烘焙参数全量          │
  │    • 质检结果: 各 Gate 通过/失败/重试次数     │
  └────────────────────────────────────────────┘
                        
新任务进入 Stage 1 时:
  ┌────────────────────────────────────────────┐
  │ 从 ChromaDB 检索最相似的 K 个历史案例        │
  │    • 相似度: 输入特征向量余弦距离            │
  │    • 成功案例: 复用其策略参数作为初始推荐      │
  │    • 失败案例: 该参数组合加入排除列表          │
  └────────────────────────────────────────────┘
```

**自愈逻辑**：

| 场景 | 行为 |
|------|------|
| 新输入与历史成功案例匹配 | Agent 直接推荐该案例的参数，质检标准按该模型类型的历史表现自动缩放 |
| 新输入与历史失败案例匹配 | Agent 避开该参数组合，选择次优方案，同时降低对应质检阈值（更严格） |
| 同一模型反复在同一 Gate 失败 | 知识库中该模式失败计数 +1，达到 3 次后触发规则更新流程——LLM 重新评估质检规则并生成修正建议 |
| 用户手动调整参数后成功 | 系统记录该调整，下次同类型输入时优先使用调整后的参数 |

> Adaptive Standards 使 TopoFlow 的质检规则随着时间的推移越来越精准——每一笔失败的记录都是知识库的一次进化。

### 11.4 规则可配置性

```toml
[standards]
engine_target = "ue5"     # ue5 / unity / custom
face_budget = "medium"    # low / medium / high / custom
uv_resolution = 2048
normal_space = "directx"

[standards.gate_a_topology]
max_triangle_pct = 5.0
max_face_density_variance = 0.3
require_watertight = true

[standards.gate_b_uv]
min_island_gap_px = 4
min_first_quadrant_utilization = 0.8
max_stretch_pct = 3.0

[standards.gate_c_bake]
normal_color_space = "linear"
ao_color_space = "srgb"
```

---

## 12. REST API 设计

### 12.1 设计目标

将 TopoFlow 从本地桌面工具扩展为**可集成的后端服务**，支持其他系统（CI/CD、运营平台、测试平台）通过标准化接口调用管线能力。

### 12.2 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/tasks` | 提交任务（上传设计图 + 配置参数），返回 `task_id` |
| `GET` | `/api/v1/tasks/{task_id}` | 查询任务状态（pending / running / passed / failed）和进度摘要 |
| `GET` | `/api/v1/tasks/{task_id}/result` | 下载任务输出产物（zip 包或各文件单独下载） |
| `POST` | `/api/v1/webhook` | 注册回调 URL，任务完成时自动推送结果 |
| `GET` | `/api/v1/presets` | 获取可用引擎预设和 style profile 列表 |
| `POST` | `/api/v1/validate` | 仅执行质检（不上管线），输入 OBJ 输出质检报告 JSON |

### 12.3 任务状态流转

```
提交 → pending → running → passed  → done
                        → failed  → 暂停（等用户人工介入）
```

### 12.4 API 集成场景

| 场景 | 说明 |
|------|------|
| 游戏运营平台调用 | 运营上传角色设计图 → 自动生成 3D 资产 → 直接入库 |
| CI/CD 集成 | 美术提交设计图到 Git → webhook 触发 TopoFlow → 自动生成并推送资产到引擎仓库 |
| 测试平台调用 | 批量提交模型 → 仅走质检管线（`/validate`）→ 收集质检报告做质量大盘 |

### 12.5 Web 可视化看板

Gate 质检报告输出为 **HTML 交互页面**而非纯 JSON：

- 雷达图展示四项拓扑指标（三角面占比 / 极点分布 / 面密度方差 / TopoStrain）
- TopoVision 热力图预览（嵌入 360° 模型视图）
- 各阶段耗时条形图
- 横向对比：历史任务质检指标趋势

技术选型：Chart.js / ECharts（纯前端，零后端依赖）

### 12.6 Go 质检 CLI（可选模块）

将 Gate A 质检逻辑从 Python 中抽离，用 **Go 语言**实现为独立 CLI 工具，用于展示 Go 工程能力和跨语言系统设计。

**设计目标**：
- 不依赖 Python 运行环境，可独立分发为单二进制文件
- 输入 OBJ 文件，输出 JSON 格式质检报告
- 与主管线解耦，支持单独调用或集成至 CI/CD 流程

**CLI 接口**：

```
topoflow-qc check model.obj --output report.json
topoflow-qc batch ./input_dir/ --output ./reports/
topoflow-qc version
```

**实现范围**（核心算法 ~300 行 Go 代码）：

| 模块 | 说明 |
|------|------|
| OBJ 解析器 | 手写轻量解析，读取顶点/三角面/法线数据 |
| 四边面占比统计 | 从三角面推断原始四边形拓扑 |
| 极点分布分析 | 逐顶点价数统计，标记高变形区域 |
| 面密度方差 | 基于局部邻域的面密度均匀度计算 |
| TopoStrain 评分 | 移植核心算法：cotangent Laplacian → 曲率-流向偏离角 |
| TopoVision 热力图 | 输出带顶点色的 OBJ（可视化） |

**集成方式**：

```
Flow A: TopoFlow 主管线 (Python)
          → Stage 4 时调用 topoflow-qc 子进程
          → 读取 stdout JSON 作为 Gate A 结果

Flow B: 独立使用
          → 美术/TA 直接运行 CLI 质检模型
          → 输出 JSON + 热力图 OBJ
```

---

## 13. 技术栈与工具清单

### 13.1 软件依赖

| 组件 | 技术选型 | 用途 | 许可证 |
|------|---------|------|--------|
| **Agent 大脑** | OpenAI GPT-4o / Claude Sonnet | LLM 分析与决策 | API 调用 |
| **Agent 框架** | LangGraph | 状态图与工具循环 | MIT |
| **后端运行时** | Python 3.11+ | 主程序语言 | PSF |
| **API 服务** | FastAPI + Uvicorn | RESTful API 层 | MIT |
| **质检 CLI（可选）** | Go (Golang) | 独立 Gate A 质检工具 | — |
| **可视化仪表盘** | Chart.js / ECharts | 质检报告交互图表 | MIT |
| **缓存与队列** | Redis | 任务队列后端 / 可选缓存层 / 状态发布订阅 | Redis Labs |
| **3D 生成 API** | Meshy Image-to-3D | 设计图 → 脏模型 | API |
| **备选生成** | TripoSR | 兜底生成方案 | MIT |
| **网格处理** | trimesh, pymeshlab | 预处理/诊断/分析 | MIT/GPL |
| **重拓扑** | QuadRemesher CLI | 有机体重拓扑 | 商业许可 |
| **备重重拓扑** | Instant Meshes | 备选方案 | MIT |
| **UV 打包** | UVPackmaster (Blender 脚本) | 紧密 UV 打包 | 商业许可 |
| **烘焙/渲染** | Blender 无头 (bpy + Cycles) | 法线/AO/曲率烘焙 | GPL |
| **向量数据库** | ChromaDB | 工业标准与偏好存储 | Apache 2.0 |
| **Web UI** | Gradio | 浏览器交互界面 | Apache 2.0 |
| **CLI** | argparse + rich | 命令行交互 | MIT |
| **打包分发** | PyInstaller | 独立可执行文件 | GPL |

### 13.2 Blender 无头模式调用规范

```python
# 调用示例（内部脚本）
blender --background --python bake_script.py -- \
    --low_poly "stage5_low_uv.fbx" \
    --high_poly "stage0_raw.obj" \
    --output_dir "./output/maps/" \
    --bake_resolution 2048 \
    --normal_space "directx" \
    --cage_distance 0.01 \
    --samples 256
```

### 13.3 系统最低要求

| 资源 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 4 核 x86-64 | 8 核以上 |
| 内存 | 16 GB | 32 GB |
| GPU | NVIDIA GTX 1060 6GB | RTX 3060+ |
| 存储 | 10 GB 可用 | SSD |
| 网络 | 宽带（API 调用） | 低延迟连接 |
| 操作系统 | Windows 10 64-bit | Windows 11 |

### 13.4 打包分发策略

```
TopoFlow Standalone Package
├── topoflow.exe            # PyInstaller 主入口
├── _internal/              # 内置 Python 环境
│   ├── python/
│   ├── site-packages/
│   └── blender_bin/        # 内置 Blender 运行库（blender.exe 无头模式）
├── config.toml             # 用户配置文件
├── knowledge_base/         # ChromaDB 持久化存储
└── logs/                   # 运行日志
```

---

## 14. 交付物与成功标准

### 14.1 交付物清单

| 交付物 | 说明 |
|--------|------|
| **可执行应用** | Windows 版独立安装包（.exe），无需预装 Blender 或其他 DCC |
| **源代码仓库** | 完整源码，含 LangGraph 管线定义、各 Stage 执行器、质检模块、Web UI |
| **配置文件** | `config.toml`，含引擎目标/质检阈值/API Keys 配置 |
| **验证案例集** | ≥ 5 张不同风格设计图的处理结果，全部通过三重质检 |
| **项目文档** | 本文档 + 架构图 + API 说明 + 工业标准定义文件 |

### 14.2 成功标准

| 指标 | 目标值 | 测量方式 |
|------|--------|---------|
| 端到端耗时 | ≤ 20 min / 个（含 AI 生成） | 10 次运行取中位数 |
| 质检一次通过率 | ≥ 70% | 按 Gate A/B/C 分别统计 |
| 用户手动调整减少 | ≥ 80%（对比纯手工流程） | 对比实验 |
| 资产可用性 | 100% 可直接导入 UE5 正确显示 | 导入验证测试 |
| API 调用成功率 | ≥ 95% | 含重试后的最终成功率 |
| 失败自愈率 | ≥ 60%（自动重试成功 / 总失败数） | 自动恢复统计 |

### 14.3 验证案例集建议

重点覆盖**风格化卡通和古风角色**，与 TopoFlow 的目标场景一致：

| # | 设计图类型 | 风格 | Style Profile | 关键检测点 |
|---|-----------|------|--------------|-----------|
| 1 | 女性角色正面立绘 | **风格化卡通** | stylized_cartoon | 面部拓扑、TopoStrain 评分、热力图 |
| 2 | 古风蛇妖女性（半身细节） | **古风风格化** | stylized_cartoon | 服饰褶皱拓扑引导、高领区域曲率对齐 |
| 3 | 男性全身着甲 | PBR 写实 | pbr_realistic | 硬表面重拓扑、硬边处理、风格对比基线 |
| 4 | 四足生物 | **风格化卡通** | stylized_cartoon | 关节拓扑、对称性、topostrain 变形预测 |
| 5 | 道具（武器） | 半写实 | semi_realistic | UV 打包效率、硬边 |
| 6 | 复杂服饰角色（宽袖长裙） | **古风风格化** | stylized_cartoon | 拓扑流向引导、密集服饰区域细节保留 |

> 案例 2、4、6 按风格化标准执行：目标面数更低（6K-8K），质检阈值更宽松，确保输出资产既满足引擎要求又避免过度拓扑带来的面数浪费。

---

## 15. 附录：运行模式说明

### 15.1 运行模式一览

| 模式 | 描述 | 适用场景 |
|------|------|---------|
| **交互模式** (默认) | Web UI 启动，用户上传 → 确认策略 → 查看结果 | 日常使用、调试 |
| **API Server 模式** | `topoflow serve --port 8080` 启动 REST API 服务 | 系统集成、CI/CD、平台化部署 |
| **Auto-pilot 模式** | 丢图即走，全部自动决策，仅失败时暂停报错 | 批量处理、夜跑 |
| **CLI 模式** | `topoflow run --input design.png --output ./asset` | 脚本集成、CI/CD |
| **Watch 模式** | `topoflow watch --folder ./incoming/` | 监控文件夹，自动处理新图 |
| **仅质检模式** | `topoflow inspect --model model.fbx` | 仅执行三重质检，不走管线 |

### 15.2 配置文件映射

```toml
[general]
output_dir = "./output"
temp_dir = "./.temp"
keep_temp = false
log_level = "info"

[run_mode]
default = "interactive"   # interactive / api_server / auto_pilot / cli / watch / inspect_only
auto_pilot = false         # 是否跳过 Stage 2 人工确认
watch_folder = ""          # Watch 模式监控目录
engine_preset = "ue5_nanite"  # ue5_nanite / unity / mobile / custom
api_port = 8080            # API Server 模式监听端口
api_webhook = ""           # 全局 webhook 回调 URL（可选）

[api_keys]
meshy = ""                 # Meshy API Key
openai = ""                # OpenAI API Key
anthropic = ""             # Anthropic API Key (备选)

[performance]
max_workers = 1
worker_timeout = 3600
cache_enabled = true
cache_max_entries = 20
cache_backend = "file"       # file / redis

[redis]
host = "127.0.0.1"
port = 6379
db = 0
password = ""
queue_enabled = false        # 是否使用 Redis 作为任务队列后端
cache_enabled = false         # 是否使用 Redis 作为缓存后端
```

---

> **文档状态**：最终版设计文档，可直接转入工程生产  
> **版本**：v3.0  
> **日期**：2026-07-13  
> **关于此文档**：此文档可作为求职简历的项目附件，展示完整的工业级产品设计、系统架构和工程思维能力。

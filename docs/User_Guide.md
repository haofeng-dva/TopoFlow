# TopoFlow 用户手册

## 快速启动

1. 确认 Blender 和团结引擎已安装。
2. 双击 `scripts/start_topoflow.cmd`，或运行 `.venv\Scripts\python.exe topoflow.py`。
3. 在 Web UI 上传 OBJ、PLY、STL、GLB 或 GLTF。
4. 目标引擎选择 `tuanjie_urp`，UV 后端保持 Blender Native。
5. 完成后下载报告或完整资产 ZIP。

## 输出

- `_high`：源模型。
- `_low`：低模与 TopoVision 热力图。
- `_maps`：Base Color、Normal、AO、Curvature、Metallic、Roughness、Emission。
- `_engine`：FBX、贴图、团结引擎导入清单。
- `report.json`：Gate A-D 审计结果。

## 质量门

- Gate A：拓扑、面密度、三角面和 TopoStrain。
- Gate B：UV 越界、退化、利用率和拉伸。
- Gate C：烘焙分辨率、法线、AO 和 PBR 通道。
- Gate D：团结引擎 Mesh、SkinnedMesh、骨骼、动画、材质和 Prefab。

## API

- `POST /api/v1/tasks`：提交任务。
- `GET /api/v1/tasks`：任务列表。
- `GET /api/v1/tasks/{id}`：状态与进度。
- `POST /api/v1/tasks/{id}/cancel`：取消任务。
- `GET /api/v1/tasks/{id}/result`：下载报告。


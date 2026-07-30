# TopoFlow Alpha 验收报告

日期：2026-07-26

## 验收环境

- Windows x64
- NVIDIA GTX 1660 Ti 6GB
- Blender 4.5.3
- 团结引擎 2022.3.62t11
- Python 3.13

## 已验证流程

- Stage 1-10 静态模型完整流程。
- Blender Native UV、Normal/AO/Curvature 烘焙。
- 默认 Base Color/Metallic/Roughness/Emission PBR 通道。
- 团结引擎材质和 Prefab 自动创建。
- RiggedFigure：19 骨骼、1 动画。
- Fox：24 骨骼、3 动画。
- DamagedHelmet：静态 PBR 模型。
- Gate A-C 自动参数修复。
- Gate D Mesh、SkinnedMesh、UV、骨骼、动画和材质验证。

## 已知限制

- 图片生成 3D 仅保留 Provider 接口，真实 Meshy 调用需要 API Key。
- UVPackmaster 4 未安装，当前固定使用 Blender Native。
- 默认 PBR 通道用于保证材质完整性，不替代专业美术贴图制作。
- Windows 安装程序未进行商业代码签名。


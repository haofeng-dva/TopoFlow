"""
Stage 3: 重拓扑

输入: high_poly.obj + strategy.json（含 retopo_method 和 style_profile）
输出: stage3_low.obj

支持四种后端:
  - "meshlab": PyMeshLab 二次误差简化（免费，默认回退）
  - "instant_meshes": Instant Meshes（免费，开源，推荐）
  - "blender_remesh": Blender 内置 Remesh 修改器（免费，需安装 Blender）
  - "quadremesher": QuadRemesher CLI（商业，$140，接口已预留）

Style-Aware 参数映射（由 strategy.style_profile 驱动）:
  - stylized_cartoon: 6000-8000 面, adaptivity 0.7, 允许三角面
  - semi_realistic: 10000-15000 面, adaptivity 1.0, 严格四边面
  - pbr_realistic: 15000-25000 面, adaptivity 1.2, 全部四边面
  - toon_anime: 4000-6000 面, adaptivity 0.5, 宽松标准
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from src.tools.blender import find_blender, run_blender_script


# Style 到重拓扑参数的映射表
STYLE_PARAMS = {
    "stylized_cartoon": {
        "target_face_count": 7000,
        "adaptivity": 0.7,
        "hard_edge_angle": 60,
        "description": "简化边缘环路，关节区域适度稀疏",
    },
    "semi_realistic": {
        "target_face_count": 12000,
        "adaptivity": 1.0,
        "hard_edge_angle": 45,
        "description": "严格四边面，面部/手部独立环路",
    },
    "pbr_realistic": {
        "target_face_count": 20000,
        "adaptivity": 1.2,
        "hard_edge_angle": 30,
        "description": "最高精度，全部四边面，解剖学环路引导",
    },
    "toon_anime": {
        "target_face_count": 5000,
        "adaptivity": 0.5,
        "hard_edge_angle": 75,
        "description": "极简拓扑，允许三角面，无严格环路要求",
    },
}

DEFAULT_STYLE = "stylized_cartoon"


def run(high_poly_path: str, strategy: dict) -> Optional[str]:
    """执行 Stage 3 重拓扑。

    Args:
        high_poly_path: 脏模型/高模路径
        strategy: 处理策略，需含:
            - retopo_method: "instant_meshes" | "blender_remesh" | "quadremesher"
            - style_profile: 风格子类型
            - target_face_count（可选，覆盖风格映射）

    Returns:
        低模 OBJ 路径，失败返回 None
    """
    style = strategy.get("style_profile", DEFAULT_STYLE)
    method = strategy.get("retopo_method", "meshlab")
    params = STYLE_PARAMS.get(style, STYLE_PARAMS[DEFAULT_STYLE]).copy()
    params["blender_path"] = strategy.get("blender_path", "")
    params["worker_timeout"] = strategy.get("worker_timeout", 600)

    # 策略中可覆盖面数
    target_faces = strategy.get("target_face_count", params["target_face_count"])

    # 输出路径
    output_dir = os.path.dirname(high_poly_path)
    low_poly_path = os.path.join(output_dir, "stage3_low.obj")

    print(f"[Stage 3] 重拓扑: method={method}, style={style}, target={target_faces}面")

    if method == "meshlab":
        success = _run_meshlab_decimation(high_poly_path, low_poly_path, target_faces)
    elif method == "instant_meshes":
        success = _run_instant_meshes(high_poly_path, low_poly_path, target_faces, params)
    elif method == "blender_remesh":
        success = _run_blender_remesh(high_poly_path, low_poly_path, target_faces, params)
    elif method == "quadremesher":
        success = _run_quadremesher(high_poly_path, low_poly_path, target_faces, params)
    else:
        print(f"[Stage 3] 不支持的重拓扑方法: {method}，回退 MeshLab")
        success = _run_meshlab_decimation(high_poly_path, low_poly_path, target_faces)

    if not success and method != "blender_remesh" and params.get("blender_path"):
        normalized = Path(low_poly_path).with_name("stage3_meshlab_input.obj")
        fallback_input = str(normalized) if normalized.is_file() else high_poly_path
        print("[Stage 3] Primary backend failed; falling back to Blender Remesh")
        success = _run_blender_remesh(fallback_input, low_poly_path, target_faces, params)

    if success and os.path.exists(low_poly_path):
        print(f"[Stage 3] 输出低模: {low_poly_path}")
        return low_poly_path

    print(f"[Stage 3] 重拓扑失败")
    return None


def _run_meshlab_decimation(input_path: str, output_path: str, target_faces: int) -> bool:
    """使用 Trimesh 规范化预算内模型，超预算时调用 PyMeshLab 简化。"""
    normalized_input = input_path
    try:
        import trimesh

        mesh = trimesh.load(input_path, force="mesh")
        if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
            print("[Stage 3] 输入模型没有可处理的面")
            return False
        if len(mesh.faces) <= target_faces:
            if Path(input_path).suffix.lower() == ".obj":
                shutil.copy2(input_path, output_path)
            else:
                mesh.export(output_path)
            print(f"[Stage 3] 当前 {len(mesh.faces)} 面已在预算内，跳过简化")
            return os.path.exists(output_path)
        if Path(input_path).suffix.lower() != ".obj":
            normalized_input = str(Path(output_path).with_name("stage3_meshlab_input.obj"))
            mesh.export(normalized_input)
    except Exception as exc:
        print(f"[Stage 3] 读取输入模型失败: {exc}")
        return False

    try:
        import pymeshlab

        mesh_set = pymeshlab.MeshSet()
        mesh_set.load_new_mesh(normalized_input)
        mesh_set.meshing_decimation_quadric_edge_collapse(
            targetfacenum=int(target_faces),
            preservenormal=True,
            preservetopology=True,
            autoclean=True,
        )
        mesh_set.save_current_mesh(output_path)
        return os.path.exists(output_path)
    except ImportError:
        print("[Stage 3] PyMeshLab 未安装，无法执行本地重拓扑")
        return False
    except Exception as exc:
        print(f"[Stage 3] MeshLab 重拓扑失败: {exc}")
        return False


# ========== 方案 A: Instant Meshes（免费，推荐） ==========

def _run_instant_meshes(
    input_path: str, output_path: str, target_faces: int, params: dict
) -> bool:
    """调用 Instant Meshes CLI 执行重拓扑。

    Instant Meshes 是开源的自动重拓扑工具，MIT 协议。
    安装: 从 https://github.com/wjakob/instant-meshes 下载 exe
          或放在 PATH 中

    CLI 用法:
        instant-meshes input.obj -o output.obj -f {face_count}
    """
    # 查找 Instant Meshes 可执行文件
    im_exe = shutil.which("instant-meshes") or shutil.which("InstantMeshes")
    if im_exe is None:
        # 常见安装路径
        candidates = [
            "C:\\Program Files\\Instant Meshes\\InstantMeshes.exe",
            "C:\\Program Files (x86)\\Instant Meshes\\InstantMeshes.exe",
            os.path.expanduser("~\\AppData\\Local\\Instant Meshes\\InstantMeshes.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                im_exe = c
                break

    if im_exe is None:
        print("[Stage 3] Instant Meshes 未安装，跳过")
        print("  下载: https://github.com/wjakob/instant-meshes/releases")
        return False

    cmd = [im_exe, input_path, "-o", output_path, "-f", str(target_faces)]
    # adaptivity → 对应 --smooth 参数（值越大越平滑）
    smooth = int(params.get("adaptivity", 0.7) * 5)
    cmd.extend(["--smooth", str(smooth)])

    print(f"[Stage 3] 执行: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return True
        print(f"[Stage 3] Instant Meshes 错误: {result.stderr[:200]}")
        return False
    except FileNotFoundError:
        print(f"[Stage 3] 未找到 Instant Meshes 可执行文件")
        return False
    except subprocess.TimeoutExpired:
        print(f"[Stage 3] Instant Meshes 超时（5分钟）")
        return False
    except Exception as e:
        print(f"[Stage 3] Instant Meshes 异常: {e}")
        return False


# ========== 方案 B: Blender 内置重拓扑（免费，需安装 Blender） ==========

def _run_blender_remesh(
    input_path: str, output_path: str, target_faces: int, params: dict
) -> bool:
    """使用 Blender Voxel Remesh 生成以四边形为主的规则网格。"""
    try:
        import trimesh
        mesh = trimesh.load(input_path, force="mesh")
        extents = mesh.bounding_box.extents
        longest = float(max(extents)) or 1.0
        voxel_size = longest / max(16.0, min(256.0, (target_faces / 6.0) ** 0.5))
    except Exception:
        voxel_size = 0.02
    script = f'''
import bpy
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.wm.obj_import(filepath={repr(str(Path(input_path).resolve()))})
mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not mesh_objects:
    raise RuntimeError("没有可重拓扑网格")
obj = mesh_objects[0]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
try:
    bpy.ops.object.quadriflow_remesh(
        mode="FACES", target_faces={int(target_faces)},
        use_mesh_symmetry=False, use_preserve_sharp=True,
        use_preserve_boundary=True, smooth_normals=True,
    )
except Exception:
    obj.data.remesh_voxel_size = {voxel_size}
    obj.data.remesh_voxel_adaptivity = 0.0
    bpy.ops.object.voxel_remesh()
bpy.ops.wm.obj_export(filepath={repr(str(Path(output_path).resolve()))}, export_selected_objects=True, export_uv=False, export_materials=False)
'''
    try:
        run_blender_script(
            script, str(Path(output_path).resolve().parent),
            params.get("blender_path", ""), int(params.get("worker_timeout", 600)),
        )
        return Path(output_path).is_file() and Path(output_path).stat().st_size > 0
    except Exception as exc:
        print(f"[Stage 3] Blender 异常: {exc}")
        return False


# ========== 方案 C: QuadRemesher（商业版，接口已预留） ==========

def _run_quadremesher(
    input_path: str, output_path: str, target_faces: int, params: dict
) -> bool:
    """调用 QuadRemesher CLI。

    QuadRemesher 是商业重拓扑软件（$140），
    本函数已预留完整接口，接入需要:
      1. 购买并安装 QuadRemesher（https://exoside.com/quadremesher/）
      2. 确保 QuadRemesher CLI 在 PATH 中

    CLI 用法参考:
        QuadRemesher input.obj -o output.obj -tf {target_faces}
    """
    qr_exe = shutil.which("QuadRemesher") or shutil.which("quadremesher")
    if qr_exe is None:
        candidates = [
            "C:\\Program Files\\QuadRemesher\\QuadRemesher.exe",
            os.path.expanduser("~\\AppData\\Local\\QuadRemesher\\QuadRemesher.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                qr_exe = c
                break

    if qr_exe is None:
        print("[Stage 3] QuadRemesher 未安装")
        print("  购买: https://exoside.com/quadremesher/")
        print("  安装后在 config.toml 中配置路径")
        return False

    cmd = [qr_exe, input_path, "-o", output_path, "-tf", str(target_faces)]

    # adaptivity → QuadRemesher 的 --adaptivity 参数
    adp = params.get("adaptivity", 1.0)
    cmd.extend(["--adaptivity", str(adp)])

    # 硬边角度
    cmd.extend(["--hard-edge-angle", str(params.get("hard_edge_angle", 60))])

    print(f"[Stage 3] 执行: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0 and os.path.exists(output_path):
            return True
        print(f"[Stage 3] QuadRemesher 错误: {result.stderr[:200]}")
        return False
    except FileNotFoundError:
        print(f"[Stage 3] QuadRemesher 未找到")
        return False
    except subprocess.TimeoutExpired:
        print(f"[Stage 3] QuadRemesher 超时")
        return False
    except Exception as e:
        print(f"[Stage 3] QuadRemesher 异常: {e}")
        return False

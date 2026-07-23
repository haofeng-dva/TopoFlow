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
from typing import Optional


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

    if success and os.path.exists(low_poly_path):
        print(f"[Stage 3] 输出低模: {low_poly_path}")
        return low_poly_path

    print(f"[Stage 3] 重拓扑失败")
    return None


def _run_meshlab_decimation(input_path: str, output_path: str, target_faces: int) -> bool:
    """使用 Trimesh 规范化预算内模型，超预算时调用 PyMeshLab 简化。"""
    try:
        import trimesh

        mesh = trimesh.load(input_path, force="mesh")
        if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
            print("[Stage 3] 输入模型没有可处理的面")
            return False
        if len(mesh.faces) <= target_faces:
            mesh.export(output_path)
            print(f"[Stage 3] 当前 {len(mesh.faces)} 面已在预算内，跳过简化")
            return os.path.exists(output_path)
    except Exception as exc:
        print(f"[Stage 3] 读取输入模型失败: {exc}")
        return False

    try:
        import pymeshlab

        mesh_set = pymeshlab.MeshSet()
        mesh_set.load_new_mesh(input_path)
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
    """调用 Blender 无头模式执行 Remesh 修改器。

    需要: blender.exe 在 PATH 中或安装在默认路径。

    原理:
      1. 导入 OBJ
      2. 应用 Remesh 修改器（Sharp 模式保持硬边）
      3. 导出为 OBJ
    """
    blender_exe = shutil.which("blender")
    if blender_exe is None:
        candidates = [
            "C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender 3.6\\blender.exe",
            os.path.expanduser("~\\AppData\\Local\\Programs\\Blender\\blender.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                blender_exe = c
                break

    if blender_exe is None:
        print("[Stage 3] Blender 未安装，跳过")
        return False

    # 生成 Blender Python 脚本
    script = f"""
import bpy
import sys

# 清除默认场景
bpy.ops.wm.read_factory_settings(use_empty=True)

# 导入 OBJ
bpy.ops.wm.obj_import(filepath="{input_path.replace(os.sep, '/')}")

# 应用 Remesh 修改器
obj = bpy.context.selected_objects[0]
mod = obj.modifiers.new(name="Remesh", type='REMESH')
mod.mode = 'SHARP'  # Sharp 模式：保留硬边，适合风格化
mod.octree_depth = 8  # 精度
mod.scale = 0.99

# 应用修改器
bpy.ops.object.modifier_apply(modifier=mod.name)

# 导出 OBJ
bpy.ops.wm.obj_export(filepath="{output_path.replace(os.sep, '/')}")
"""
    script_path = os.path.join(os.path.dirname(output_path), "_blender_remesh.py")
    with open(script_path, "w") as f:
        f.write(script)

    cmd = [blender_exe, "--background", "--python", script_path]
    print(f"[Stage 3] 执行 Blender 重拓扑...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        os.remove(script_path)
        if result.returncode == 0 and os.path.exists(output_path):
            return True
        print(f"[Stage 3] Blender 错误: {result.stderr[-300:]}")
        return False
    except Exception as e:
        os.remove(script_path)
        print(f"[Stage 3] Blender 异常: {e}")
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

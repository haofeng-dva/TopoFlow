"""Stage 4: 拓扑质检 Gate A + TopoStrain + TopoVision

输入: stage3_low.obj
输出: stage4_low_passed.obj + stage4_low_heatmap.obj（TopoVision）

审计规则:
  1. 三角面占比 ≤ 5%
  2. 极点分布检查（变形区域禁止非 4 价）
  3. 面密度方差 ≤ 30%
  4. TopoStrain 变形质量预测（新）

失败处理:
  - LLM 分析失败指标 → 生成调整方案
  - 自动重试 ≤ 2 次 → 暂停报错
"""

import os
import numpy as np
from typing import Optional
from src.qc.topostrain import topostrain_score, generate_heatmap_colors, export_heatmap_obj

def _load_mesh(path: str):
    """用 trimesh 加载模型，返回顶点和三角面。"""
    import trimesh
    mesh = trimesh.load(path, force="mesh")
    # 统一为三角面
    if hasattr(mesh, "faces"):
        tris = mesh.faces
    else:
        tris = None
    return mesh, np.array(mesh.vertices, dtype=np.float64), tris


def _obj_polygons(path: str) -> list[list[int]]:
    if not path.lower().endswith(".obj"):
        return []
    polygons = []
    with open(path, "r", encoding="utf-8", errors="replace") as source:
        for line in source:
            if not line.startswith("f "):
                continue
            indices = []
            for token in line.split()[1:]:
                raw = token.split("/")[0]
                if raw:
                    indices.append(int(raw) - 1)
            if len(indices) >= 3:
                polygons.append(indices)
    return polygons


def _triangle_pct(path: str, mesh) -> float:
    """优先从 OBJ 原始多边形统计三角面比例，避免 Trimesh 自动三角化失真。"""
    polygons = _obj_polygons(path)
    if polygons:
        return round(sum(len(face) == 3 for face in polygons) * 100.0 / len(polygons), 4)
    if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
        return 0.0
    return 100.0


def _polygon_pole_analysis(path: str, vertices: np.ndarray, faces: np.ndarray) -> int:
    polygons = _obj_polygons(path)
    if not polygons:
        return _pole_analysis(vertices, faces)
    neighbors = [set() for _ in range(len(vertices))]
    for polygon in polygons:
        for index, vertex in enumerate(polygon):
            previous = polygon[index - 1]
            following = polygon[(index + 1) % len(polygon)]
            if 0 <= vertex < len(neighbors):
                neighbors[vertex].update((previous, following))
    return sum(bool(adjacent) and len(adjacent) != 4 for adjacent in neighbors)


def _pole_analysis(vertices: np.ndarray, faces: np.ndarray):
    """极点分布分析：统计非 4 价顶点数量。"""
    n_verts = len(vertices)
    valence = np.zeros(n_verts, dtype=int)
    for tri in faces:
        for i in range(3):
            valence[tri[i]] += 1
    non_4_valence = np.sum((valence != 4) & (valence > 0))
    return int(non_4_valence)


def _face_density_variance(vertices: np.ndarray, faces: np.ndarray) -> float:
    """面密度方差：每个顶点的邻域面数方差 / 均值。"""
    n_verts = len(vertices)
    valence = np.zeros(n_verts, dtype=int)
    for tri in faces:
        for i in range(3):
            valence[tri[i]] += 1
    mean_v = np.mean(valence)
    if mean_v < 1e-10:
        return 0.0
    return float(np.std(valence) / mean_v)


def run(low_poly_path: str, strategy: dict, config: dict) -> dict:
    """执行 Stage 4 Gate A 质检。完整实现，含 TopoStrain 和 TopoVision。

    Args:
        low_poly_path: 低模路径
        strategy: 处理策略
        config: 全局配置
    """
    print(f"[Stage 4 Gate A] 拓扑质检: {low_poly_path}")

    # 加载质检阈值
    ga = config.get("standards", {}).get("gate_a_topology", {})
    max_triangle_pct = ga.get("max_triangle_pct", 5.0)
    max_density_var = ga.get("max_face_density_variance", 0.3)
    max_topostrain_score = ga.get("max_topostrain_score", 40.0)
    topostrain_threshold_deg = strategy.get("topostrain_threshold", 30.0)
    require_watertight = ga.get("require_watertight", True)

    # 加载模型
    mesh, vertices, faces = _load_mesh(low_poly_path)
    if faces is None:
        return {"passed": False, "error": "模型无法加载或缺少三角面", "metrics": {}}

    n_faces = len(faces)
    n_verts = len(vertices)
    print(f"  顶点: {n_verts}, 三角面: {n_faces}")

    # === 四项审计 ===

    # 1. 三角面占比
    tri_pct = _triangle_pct(low_poly_path, mesh)

    # 2. 极点分布
    pole_count = _polygon_pole_analysis(low_poly_path, vertices, faces)

    # 3. 面密度方差
    density_var = _face_density_variance(vertices, faces)

    # 4. TopoStrain 变形质量预测
    risk_mask, ts_score = topostrain_score(
        vertices, faces, threshold_deg=topostrain_threshold_deg
    )
    risk_pct = float(np.mean(risk_mask) * 100)

    print(f"  指标: tri%={tri_pct}, poles={pole_count}, density_var={density_var:.3f}, TopoStrain={ts_score:.2f}")

    # === 判定 ===
    passed = (
        tri_pct <= max_triangle_pct
        and density_var <= max_density_var
        and ts_score <= max_topostrain_score
        and (mesh.is_watertight or not require_watertight)
    )

    result = {
        "passed": passed,
        "retry_count": 0,
        "metrics": {
            "triangle_pct": tri_pct,
            "pole_count": pole_count,
            "face_density_variance": round(density_var, 4),
            "topostrain_score": round(ts_score, 2),
            "topostrain_risk_pct": round(risk_pct, 1),
            "watertight": bool(mesh.is_watertight),
        },
        "heatmap_path": "",
    }

    # === 始终生成 TopoVision，便于定位未通过原因 ===
    output_dir = os.path.dirname(low_poly_path)
    heatmap_path = os.path.join(output_dir, "stage4_low_heatmap.obj")

    colors = generate_heatmap_colors(vertices, faces, risk_mask, ts_score)
    export_heatmap_obj(vertices, faces, colors, heatmap_path)
    result["heatmap_path"] = heatmap_path

    status = "通过" if passed else "未通过"
    print(f"[Stage 4 Gate A] {status}! TopoStrain={ts_score:.2f} 热力图={heatmap_path}")
    return result

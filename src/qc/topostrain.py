"""
TopoStrain — 基于曲率-拓扑对齐的变形质量预测算法

核心思想：
  好的拓扑应该"顺着"表面曲率走。边缘环路应环绕高曲率区域（手指、眼窝、鼻翼），
  而非横穿它们。TopoStrain 度量每个顶点的局部拓扑流向与主曲率方向的偏离程度。

算法步骤（v2 修正版）：
  1. 计算逐顶点法线
  2. 在每个顶点的切平面上，分析相邻顶点法线的变化方向 → 估计曲率方向
  3. PCA 分析一环邻域 → 估计局部拓扑流向（沿表面切向）
  4. 计算切平面上曲率方向与拓扑流向的偏离角
  5. 输出 per-vertex risk mask + 全局评分（0=完美，100=极差）

修正说明：
  v1 错误地将法向曲率向量（垂直于表面）与流向（沿表面）直接比较，
  这两种方向在这种比较中天然正交。v2 将两者都投影到切平面再比较。
"""

import numpy as np
from typing import Tuple


def topostrain_score(
    vertices: np.ndarray,
    faces: np.ndarray,
    threshold_deg: float = 30.0
) -> Tuple[np.ndarray, float]:
    """
    计算 TopoStrain 评分。

    参数:
        vertices: (N, 3) 顶点坐标数组
        faces: (M, 3) 三角面索引数组
        threshold_deg: 偏离角阈值（度），超过此角度标记为高风险

    返回:
        risk_mask: (N,) bool 数组，True = 变形高风险顶点
        global_score: float，0~100，越低越好
    """
    threshold = np.deg2rad(threshold_deg)

    # Step 1: 计算逐顶点法线和切平面
    vertex_normals = _compute_vertex_normals(vertices, faces)

    # Step 2: 计算切平面上的曲率方向
    curvature_dirs = _estimate_curvature_directions(vertices, faces, vertex_normals)

    # Step 3: PCA 分析一环邻域 → 拓扑流向（投影到切平面）
    flow_directions = _estimate_flow_directions(vertices, faces, vertex_normals)

    # Step 4: 计算切平面上两个方向的偏离角
    angles = _compute_tangent_deviation_angles(curvature_dirs, flow_directions)

    # Step 5: 标记高风险顶点
    risk_mask = angles > threshold

    # Step 6: 全局评分
    scores = 1.0 / (1.0 + np.exp(-(angles - threshold) * 5.0))
    global_score = float(100.0 * np.mean(scores))

    return risk_mask, global_score


def _compute_vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """
    计算逐顶点法线。用面法线的角度加权平均。

    返回:
        (N, 3) 单位法线数组
    """
    n_verts = len(vertices)

    # 面法线
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    face_normals = np.cross(v1 - v0, v2 - v0)
    fn_norm = np.linalg.norm(face_normals, axis=1, keepdims=True)
    fn_norm[fn_norm[:, 0] < 1e-10] = 1.0
    face_normals = face_normals / fn_norm

    # 每个面的三个角的角度
    e01 = v1 - v0
    e12 = v2 - v1
    e20 = v0 - v2

    def angle_at_vertex(e1, e2):
        dot = np.einsum('ij,ij->i', -e1, e2)
        norm = np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1)
        norm[norm < 1e-10] = 1.0
        return np.arccos(np.clip(dot / norm, -1.0, 1.0))

    angles_v0 = angle_at_vertex(e01, -e20)
    angles_v1 = angle_at_vertex(-e01, e12)
    angles_v2 = angle_at_vertex(e20, -e12)

    # 累加到顶点
    vn = np.zeros((n_verts, 3))
    for i, (angle, fn) in enumerate([
        (angles_v0, face_normals),
        (angles_v1, face_normals),
        (angles_v2, face_normals),
    ]):
        vi = faces[:, i]
        for j in range(3):
            np.add.at(vn, vi, angle[:, np.newaxis] * fn)

    # 归一化
    vn_norm = np.linalg.norm(vn, axis=1, keepdims=True)
    vn_norm[vn_norm[:, 0] < 1e-10] = 1.0
    return vn / vn_norm


def _estimate_curvature_directions(
    vertices: np.ndarray, faces: np.ndarray, normals: np.ndarray
) -> np.ndarray:
    """
    在切平面上估计曲率方向。

    方法:
      对每个顶点，收集一环邻域顶点的法线差异，
      投影到切平面上做 PCA — 第一主成分 = 最大法线变化方向 ≈ 主曲率方向。

    返回:
        (N, 3) 切平面上的主曲率方向（单位向量）
    """
    n_verts = len(vertices)
    adj = _build_adjacency(n_verts, faces)

    curvature_dirs = np.zeros((n_verts, 3))

    for i in range(n_verts):
        nbrs = adj[i]
        if len(nbrs) < 3:
            curvature_dirs[i] = _arbitrary_tangent(normals[i])
            continue

        # 法线差异：相邻顶点法线 - 当前顶点法线
        ndiff = normals[nbrs] - normals[i]

        # 投影到切平面（去掉法线方向分量）
        proj = ndiff - np.outer(np.dot(ndiff, normals[i]), normals[i])

        # PCA 分析投影后的法线差异
        centered = proj - proj.mean(axis=0)
        cov = centered.T @ centered / (len(nbrs) - 1)
        _, _, vh = np.linalg.svd(cov)

        # 第一主成分 = 法线变化最快的切向方向 ≈ 主曲率方向
        dir_i = vh[0]

        # 确保在切平面上
        dir_i = dir_i - np.dot(dir_i, normals[i]) * normals[i]
        d_norm = np.linalg.norm(dir_i)
        if d_norm < 1e-10:
            dir_i = _arbitrary_tangent(normals[i])
        else:
            dir_i = dir_i / d_norm

        curvature_dirs[i] = dir_i

    return curvature_dirs


def _estimate_flow_directions(
    vertices: np.ndarray, faces: np.ndarray, normals: np.ndarray
) -> np.ndarray:
    """
    对每个顶点，用 PCA 分析一环邻域 → 拓扑流向（投影到切平面）。

    返回:
        (N, 3) 切平面上的拓扑流向单位向量
    """
    n_verts = len(vertices)
    adj = _build_adjacency(n_verts, faces)

    flow_directions = np.zeros((n_verts, 3))

    for i in range(n_verts):
        nbrs = adj[i]
        if len(nbrs) < 3:
            flow_directions[i] = _arbitrary_tangent(normals[i])
            continue

        # 邻域顶点坐标 → PCA
        local_points = vertices[nbrs]
        center = local_points.mean(axis=0)
        centered = local_points - center
        cov = centered.T @ centered / (len(nbrs) - 1)
        _, _, vh = np.linalg.svd(cov)

        # 第一主成分 = 邻域分布最分散的方向
        flow = vh[0]

        # 投影到切平面
        flow = flow - np.dot(flow, normals[i]) * normals[i]
        f_norm = np.linalg.norm(flow)
        if f_norm < 1e-10:
            flow = _arbitrary_tangent(normals[i])
        else:
            flow = flow / f_norm

        flow_directions[i] = flow

    return flow_directions


def _compute_tangent_deviation_angles(
    curvature_dirs: np.ndarray, flow_directions: np.ndarray
) -> np.ndarray:
    """
    计算切平面上曲率方向与拓扑流向之间的偏离角。

    两者都是切向量，直接算夹角。

    返回:
        (N,) 数组，弧度制，范围 [0, π/2]
    """
    dot = np.einsum('ij,ij->i', curvature_dirs, flow_directions)
    dot = np.clip(np.abs(dot), 0.0, 1.0)
    return np.arccos(dot)


def _build_adjacency(n_verts: int, faces: np.ndarray) -> list:
    """构建邻接表"""
    adj = [[] for _ in range(n_verts)]
    for tri in faces:
        for i in range(3):
            adj[tri[i]].append(tri[(i + 1) % 3])
            adj[tri[i]].append(tri[(i + 2) % 3])
    return [list(set(nbrs)) for nbrs in adj]


def _arbitrary_tangent(normal: np.ndarray) -> np.ndarray:
    """给定法线，构造一个任意切向量"""
    if abs(normal[2]) < 0.9:
        t = np.cross(normal, np.array([0.0, 0.0, 1.0]))
    else:
        t = np.cross(normal, np.array([1.0, 0.0, 0.0]))
    t = t / (np.linalg.norm(t) + 1e-10)
    return t


# ========== 以下函数保持不变（TopoVision 可视化） ==========


def generate_heatmap_colors(
    vertices: np.ndarray,
    faces: np.ndarray,
    risk_mask: np.ndarray,
    global_score: float
) -> np.ndarray:
    """生成 TopoVision 热力图顶点色"""
    n_verts = len(vertices)

    # 每个顶点的风险评分
    risk = np.zeros(n_verts)
    if np.any(risk_mask):
        center = np.mean(vertices, axis=0)
        distances = np.linalg.norm(vertices - center, axis=1)
        span = float(np.ptp(distances))
        normalized = (distances - float(np.min(distances))) / span if span > 1e-12 else np.zeros(n_verts)
        base_risk = max(0.5, min(1.0, float(global_score) / 100.0))
        risk[risk_mask] = np.clip(0.7 * base_risk + 0.3 * normalized[risk_mask], 0.5, 1.0)

    colors = np.zeros((n_verts, 3))
    for i in range(n_verts):
        r = risk[i]
        if r < 0.3:
            colors[i] = [0.2, 0.8, 0.2]
        elif r < 0.6:
            colors[i] = [0.8, 0.8, 0.2]
        else:
            colors[i] = [0.8, 0.2, 0.2]

    return colors


def export_heatmap_obj(
    vertices: np.ndarray,
    faces: np.ndarray,
    colors: np.ndarray,
    output_path: str
):
    """导出带顶点色的 TopoVision 热力图 OBJ"""
    with open(output_path, 'w') as f:
        f.write("# TopoVision Topology Health Heatmap\n")
        f.write(f"# Vertices: {len(vertices)}, Faces: {len(faces)}\n\n")

        for v, c in zip(vertices, colors):
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}\n")

        f.write("\n")
        for tri in faces:
            f.write(f"f {tri[0]+1} {tri[1]+1} {tri[2]+1}\n")

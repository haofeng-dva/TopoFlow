"""
Stage 1: 预处理与诊断

输入: stage0_raw.obj（或直接传入的高模路径）
输出: strategy.json + diagnosis_report.json

流程:
  1. 用 trimesh 加载模型
  2. 预处理: 合并顶点、法线统一、修复非流形、归一化尺寸
  3. 诊断分析: 面数/拓扑/边界/曲率
  4. 调用 LLM 分析诊断数据 → 输出处理策略（含 style_profile）
"""

import os
import json
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class DiagnosisReport:
    """诊断报告数据结构"""
    total_vertices: int = 0
    total_faces: int = 0
    triangle_pct: float = 100.0
    boundary_edges: int = 0
    watertight: bool = True
    non_manifold_edges: int = 0
    bounding_box: list = field(default_factory=lambda: [0, 0, 0, 0, 0, 0])
    surface_area: float = 0.0
    mean_face_density: float = 0.0
    face_density_variance: float = 0.0
    pole_count: int = 0
    semantic_hints: list = field(default_factory=list)


def _load_and_preprocess(path: str):
    """加载模型并做基础预处理。"""
    import trimesh

    mesh = trimesh.load(path, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"无法加载为三角网格: {path}")

    # 合并重复顶点
    mesh.merge_vertices(merge_tex=True, merge_norm=True)

    # 统一法线
    mesh.fix_normals()

    # 尝试修复非流形
    if not mesh.is_watertight:
        try:
            trimesh.repair.fill_holes(mesh)
        except Exception:
            pass

    return mesh


def _analyze_topology(mesh) -> DiagnosisReport:
    """执行拓扑诊断分析。"""
    report = DiagnosisReport()

    # 基础统计
    report.total_vertices = len(mesh.vertices)
    report.total_faces = len(mesh.faces)
    report.bounding_box = list(mesh.bounds.flatten())
    report.surface_area = float(mesh.area)

    # 水密性和边界
    report.watertight = mesh.is_watertight
    if hasattr(mesh, "edges_unique_inverse"):
        edge_face_counts = np.bincount(mesh.edges_unique_inverse)
        report.boundary_edges = int(np.sum(edge_face_counts == 1))
        report.non_manifold_edges = int(np.sum(edge_face_counts > 2))
    else:
        report.boundary_edges = 0
        report.non_manifold_edges = 0

    # 三角面占比 (trimesh 已经全部三角化，计算退化面占比)
    # 检查是否有面积接近0的退化面
    face_areas = mesh.area_faces
    degenerate = np.sum(face_areas < 1e-8)
    report.triangle_pct = 100.0 * (1 - degenerate / max(len(face_areas), 1))

    # 面密度分析（逐顶点价数）
    valence = np.zeros(report.total_vertices, dtype=int)
    for tri in mesh.faces:
        for i in range(3):
            valence[tri[i]] += 1

    report.mean_face_density = float(np.mean(valence))
    report.face_density_variance = float(np.std(valence) / (np.mean(valence) + 1e-10))

    # 极点统计（非4价顶点在变形区域的分布）
    non_4_valence = valence[(valence != 4) & (valence > 0)]
    report.pole_count = int(len(non_4_valence))

    # 曲率估计（用顶点法线变化做粗略估计）
    if hasattr(mesh, 'vertex_normals') and len(mesh.vertex_normals) > 0:
        vn = mesh.vertex_normals
        # 曲率近似: 相邻顶点法线差异的均值
        curvature_est = []
        for tri in mesh.faces:
            for i in range(3):
                vi, vj = tri[i], tri[(i + 1) % 3]
                dot = np.dot(vn[vi], vn[vj])
                curvature_est.append(np.arccos(np.clip(dot, -1.0, 1.0)))
        report.semantic_hints.append(f"mean_curvature_angle={np.mean(curvature_est):.4f}rad")

    return report


def run(mesh_path: str, config: dict) -> Tuple[dict, dict]:
    """执行 Stage 1: 加载、预处理、诊断、LLM 策略生成。

    Args:
        mesh_path: 模型文件路径 (OBJ/PLY/STL/GLB)
        config: 全局配置（含 API keys）

    Returns:
        (strategy_dict, diagnosis_dict)
    """
    print(f"[Stage 1] 加载模型: {mesh_path}")

    # 1. 加载和预处理
    mesh = _load_and_preprocess(mesh_path)

    # 2. 诊断分析
    report = _analyze_topology(mesh)

    print(f"[Stage 1] 诊断完成:")
    print(f"  顶点: {report.total_vertices}, 三角面: {report.total_faces}")
    print(f"  水密: {report.watertight}, 边界边: {report.boundary_edges}")
    print(f"  极点数: {report.pole_count}")
    print(f"  面密度方差: {report.face_density_variance:.3f}")

    # 3. 生成策略（优先用 LLM，失败则回退规则引擎）
    diagnosis_dict = asdict(report)
    strategy = _generate_strategy(diagnosis_dict, config)

    print(f"[Stage 1] 策略: {strategy['style_profile']}, {strategy['target_face_count']}面")

    return strategy, diagnosis_dict


def _generate_strategy(diagnosis: dict, config: dict) -> dict:
    """生成处理策略。优先调 LLM，失败回退规则引擎。"""
    deepseek_key = config.get("deepseek_key", "") or config.get("api_keys", {}).get("deepseek", "")

    if deepseek_key:
        from src.agents.llm_client import LLMClient
        try:
            llm = LLMClient(provider="deepseek", api_key=deepseek_key)
            strategy = llm.diagnose(diagnosis)
            # 填充缺失字段默认值
            defaults = {
                "model_type": "organic",
                "style_profile": "stylized_cartoon",
                "retopo_method": "quadremesher",
                "target_face_count": 8000,
                "uv_resolution": 2048,
                "bake_resolution": 2048,
                "normal_space": "directx",
                "preserve_features": ["face", "hands"],
                "manual_guidance_needed": False,
                "auto_pilot_eligible": True,
                "topostrain_threshold": 30.0,
            }
            for k, v in defaults.items():
                strategy.setdefault(k, v)
            print(f"[Stage 1] 使用 LLM (DeepSeek) 生成策略")
            return strategy
        except Exception as e:
            print(f"[Stage 1] LLM 策略生成失败: {e}，回退规则引擎")

    # 规则引擎回退
    target_faces = 5000
    if diagnosis["total_faces"] > 50000:
        target_faces = 12000
    elif diagnosis["total_faces"] > 20000:
        target_faces = 8000

    return {
        "model_type": "organic",
        "style_profile": "stylized_cartoon",
        "retopo_method": "meshlab",
        "target_face_count": target_faces,
        "uv_resolution": 2048,
        "bake_resolution": 2048,
        "normal_space": "directx",
        "preserve_features": ["face", "hands"],
        "manual_guidance_needed": False,
        "auto_pilot_eligible": True,
        "topostrain_threshold": 30.0,
    }

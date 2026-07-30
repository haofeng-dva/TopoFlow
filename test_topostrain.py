"""
TopoStrain 快速验证脚本（自清理）

自行生成测试网格，测试完成后自动清理输出文件。
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.qc.topostrain import (
    topostrain_score,
    generate_heatmap_colors,
    export_heatmap_obj,
)


def generate_sphere_mesh(n_phi=20, n_theta=20):
    vertices, faces = [], []
    for i in range(n_theta + 1):
        theta = i * np.pi / n_theta
        for j in range(n_phi):
            phi = j * 2 * np.pi / n_phi
            vertices.append([
                np.sin(theta) * np.cos(phi),
                np.cos(theta),
                np.sin(theta) * np.sin(phi),
            ])
    for i in range(n_theta):
        for j in range(n_phi):
            a = i * n_phi + j
            b = a + n_phi
            faces.append([a, b, (b + 1) % n_phi + i * n_phi])
            faces.append([a, (b + 1) % n_phi + i * n_phi, (a + 1) % n_phi + i * n_phi])
    return np.array(vertices, dtype=np.float64), np.array(faces, dtype=np.int64)


def main():
    passed = 0
    failed = 0

    print("=" * 50)
    print("TopoStrain 算法验证")
    print("=" * 50)

    # 测试 1: 完美球体
    print("\n[测试 1] 完美球体（期望 ≤ 30）")
    v1, f1 = generate_sphere_mesh(20, 20)
    _, s1 = topostrain_score(v1, f1, threshold_deg=30.0)
    print(f"  评分: {s1:.2f}/100")
    if s1 <= 30:
        print("  ✅ 通过")
        passed += 1
    else:
        print("  ❌ 未通过")
        failed += 1

    # 测试 2: 噪声球体
    print("\n[测试 2] 噪声球体（期望 ≥ 40）")
    np.random.seed(42)
    noise = np.random.randn(*v1.shape) * 0.15
    v2 = v1 + noise
    _, s2 = topostrain_score(v2, f2 := f1.copy(), threshold_deg=30.0)
    print(f"  评分: {s2:.2f}/100")
    if s2 >= 40:
        print("  ✅ 通过")
        passed += 1
    else:
        print("  ❌ 未通过")
        failed += 1

    # 测试 3: 区分度（噪声 > 完美）
    print(f"\n[测试 3] 区分度（期望噪声 {s2:.1f} > 完美 {s1:.1f}）")
    if s2 > s1 + 10:
        print("  ✅ 通过")
        passed += 1
    else:
        print("  ❌ 未通过")
        failed += 1

    # 测试 4: 阈值灵敏度
    print("\n[测试 4] 阈值灵敏度")
    for thresh in [20, 30, 45, 60]:
        _, s = topostrain_score(v2, f2, threshold_deg=thresh)
        print(f"  阈值={thresh}° → 评分={s:.2f}/100")

    print(f"\n{'=' * 50}")
    print(f"结果: {passed}/{passed + failed} 通过")
    print(f"{'=' * 50}")

    # 生成热力图（验证导出功能）
    risk, _ = topostrain_score(v1, f1)
    colors = generate_heatmap_colors(v1, f1, risk, s1)
    import shutil
    import uuid
    out_dir = os.path.join(os.path.dirname(__file__), ".test-tmp", f"topostrain-{uuid.uuid4().hex}")
    os.makedirs(out_dir, exist_ok=False)
    try:
        heatmap_path = os.path.join(out_dir, "test_heatmap.obj")
        export_heatmap_obj(v1, f1, colors, heatmap_path)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

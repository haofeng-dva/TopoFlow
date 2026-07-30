"""
端到端管线测试（修正版）：直接走 Stage 1 → 4 → 9
Stage 0 （需要 API key）和 Stage 3/5/6/7/8（需要外部工具）暂用骨架占位。
"""
import sys, os, json, shutil, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config
from src.pipeline.state import PipelineState
from src.pipeline import stage1_diagnose, stage3_retopo, stage4_gate_a, stage9_pack


def main():
    print("=" * 60)
    print("TopoFlow 端到端测试（真实链路: 诊断→质检→打包）")
    print("=" * 60)

    # 1. 生成测试模型
    print("\n[1] 生成测试模型...")
    from scripts.generate_test_asset import OUTPUT_DIR as ASSET_DIR
    import subprocess
    subprocess.run(
        [sys.executable, "scripts/generate_test_asset.py"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=os.path.dirname(__file__)
    )
    obj_path = os.path.join(ASSET_DIR, "test_mannequin.obj")
    if not os.path.exists(obj_path):
        print(f"  ❌ 测试模型未生成")
        return 1
    print(f"  ✅ 测试模型: {obj_path} (顶点数: 待读取)")

    import trimesh
    m = trimesh.load(obj_path, force="mesh")
    print(f"     顶点: {len(m.vertices)}, 三角面: {len(m.faces)}")

    # 2. 加载配置
    cfg = load_config("config.toml.example")
    cfg_dict = {
        "deepseek_key": cfg.deepseek_key,
        "api_keys": {"deepseek": cfg.deepseek_key},
        "standards": {
            "gate_a_topology": {
                "max_triangle_pct": cfg.standards.gate_a_topology.max_triangle_pct,
                "max_face_density_variance": cfg.standards.gate_a_topology.max_face_density_variance,
            }
        }
    }

    task_id = f"test_{uuid.uuid4().hex[:6]}"
    output_dir = os.path.join(".", "output", task_id)
    os.makedirs(output_dir, exist_ok=True)

    # 3. Stage 1: 诊断
    print(f"\n[2] Stage 1: 预处理与诊断")
    strategy, diagnosis = stage1_diagnose.run(obj_path, cfg_dict)
    print(f"    风格: {strategy['style_profile']}, 目标面数: {strategy['target_face_count']}")

    # 4. Stage 3: 重拓扑（骨架占位，复制原始模型作为低模）
    print(f"\n[3] Stage 3: 重拓扑（骨架模式）")
    low_path = os.path.join(output_dir, "stage3_low.obj")
    shutil.copy2(obj_path, low_path)
    print(f"    已复制: {low_path}")

    # 5. Stage 4: Gate A 质检 + TopoStrain
    print(f"\n[4] Stage 4: Gate A 质检")
    gate_a = stage4_gate_a.run(low_path, strategy, cfg_dict)
    ga = gate_a.get("metrics", {})
    print(f"    TopoStrain: {ga.get('topostrain_score', 'N/A')}")
    print(f"    面密度方差: {ga.get('face_density_variance', 'N/A')}")
    print(f"    结果: {'✅ 通过' if gate_a.get('passed') else '❌ 未通过'}")

    if gate_a.get("heatmap_path"):
        print(f"    TopoVision 热力图: {gate_a['heatmap_path']}")

    # 6. Stage 9: 打包
    print(f"\n[5] Stage 9: 最终打包")
    maps = {"normal": "", "ao": "", "curvature": ""}
    result = stage9_pack.run(
        task_id=task_id,
        asset_name="test_mannequin",
        high_poly_path=obj_path,
        low_poly_path=low_path,
        heatmap_path=gate_a.get("heatmap_path", ""),
        maps=maps,
        gate_a=gate_a,
        gate_b={"passed": True, "metrics": {"uv_utilization": 0.85}},
        gate_c={"passed": True, "metrics": {}},
        strategy=strategy,
        output_dir=output_dir,
    )
    print(f"    输出目录: {result.get('output_path', 'N/A')}")
    print(f"    报告文件: {result.get('report_path', 'N/A')}")

    # 7. 验证
    print(f"\n[6] 验证结果:")
    checks = [
        ("诊断报告面数 > 0", diagnosis["total_faces"] > 0),
        ("策略已生成", strategy["target_face_count"] > 0),
        ("TopoStrain 已计算", ga.get("topostrain_score", -1) >= 0),
        ("打包完成", os.path.exists(result.get("report_path", ""))),
    ]
    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")

    # 8. 清理
    print(f"\n[7] 清理...")
    shutil.rmtree(ASSET_DIR, ignore_errors=True)
    # 保留 output 目录用于查看

    print(f"\n{'=' * 60}")
    print(f"通过: {passed}/{len(checks)}")
    print(f"{'=' * 60}")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

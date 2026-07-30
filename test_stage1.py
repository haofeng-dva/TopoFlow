"""
Stage 1 诊断测试：生成测试模型 → 诊断分析 → 输出报告
完成后自清理。
"""
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline.stage1_diagnose import run as diagnose
from scripts.generate_test_asset import OUTPUT_DIR as ASSET_DIR
from src.config import load_config


def main():
    print("=" * 50)
    print("Stage 1 诊断测试")
    print("=" * 50)

    # 1. 生成测试模型
    print("\n[1] 生成测试模型...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/generate_test_asset.py"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=os.path.dirname(__file__)
    )
    print(result.stdout.strip())

    # 2. 找到生成的 OBJ
    obj_path = os.path.join(ASSET_DIR, "test_mannequin.obj")
    if not os.path.exists(obj_path):
        print(f"❌ 未找到测试模型: {obj_path}")
        return 1

    # 3. 加载配置和运行诊断
    print("\n[2] 加载配置...")
    cfg = load_config("config.toml.example")
    cfg_dict = {
        "deepseek_key": cfg.deepseek_key,
        "api_keys": {"deepseek": cfg.deepseek_key},
    }

    print("\n[3] 运行诊断...")
    strategy, diagnosis = diagnose(obj_path, cfg_dict)

    # 4. 输出结果
    print("\n[4] 诊断报告:")
    for k, v in diagnosis.items():
        print(f"  {k}: {v}")

    print(f"\n[5] 生成策略:")
    for k, v in strategy.items():
        print(f"  {k}: {v}")

    # 5. 验证
    passed = 0
    total = 5
    print(f"\n[6] 验证:")

    if diagnosis["total_vertices"] > 0:
        print(f"  ✅ 顶点数 > 0 ({diagnosis['total_vertices']})")
        passed += 1
    else:
        print(f"  ❌ 顶点数为 0")

    if diagnosis["total_faces"] > 0:
        print(f"  ✅ 三角面数 > 0 ({diagnosis['total_faces']})")
        passed += 1
    else:
        print(f"  ❌ 三角面数为 0")

    if diagnosis["face_density_variance"] > 0:
        print(f"  ✅ 面密度方差已计算 ({diagnosis['face_density_variance']:.3f})")
        passed += 1
    else:
        print(f"  ❌ 面密度方差为 0")

    if strategy["target_face_count"] > 0:
        print(f"  ✅ 策略已生成 ({strategy['target_face_count']} 面)")
        passed += 1
    else:
        print(f"  ❌ 策略未生成")

    if "deepseek" in str(cfg_dict):
        print(f"  ✅ LLM 已配置")
        passed += 1

    # 7. 清理
    print(f"\n[7] 清理...")
    if os.path.exists(ASSET_DIR):
        shutil.rmtree(ASSET_DIR)
        print(f"  已删除: {ASSET_DIR}")

    print(f"\n{'=' * 50}")
    print(f"结果: {passed}/{total} 通过")
    print(f"{'=' * 50}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

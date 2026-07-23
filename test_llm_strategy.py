"""
测试 LLM 策略生成：诊断报告 → DeepSeek → 策略 JSON
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.llm_client import LLMClient
from src.config import load_config


def main():
    print("=" * 50)
    print("LLM 策略生成测试 (DeepSeek)")
    print("=" * 50)

    # 读取 API key
    cfg = load_config("config.toml")
    if not cfg.deepseek_key:
        print("❌ config.toml 中没有配置 deepseek_key")
        return 1

    # 初始化 LLM
    llm = LLMClient(provider="deepseek", api_key=cfg.deepseek_key)
    print(f"  Provider: deepseek")
    print(f"  API Key: {cfg.deepseek_key[:8]}...")

    # 模拟诊断报告
    diagnosis = {
        "total_vertices": 430,
        "total_faces": 840,
        "triangle_pct": 100.0,
        "boundary_edges": 0,
        "watertight": False,
        "pole_count": 430,
        "mean_face_density": 5.86,
        "face_density_variance": 0.24,
        "surface_area": 9.3,
        "semantic_hints": ["mean_curvature_angle=0.3762rad"],
    }

    print(f"\n[1] 诊断报告: {json.dumps(diagnosis, indent=2)}")

    # 调用 LLM
    print(f"\n[2] 调用 DeepSeek...")
    try:
        strategy = llm.diagnose(diagnosis)
        print(f"\n[3] 策略输出:")
        print(json.dumps(strategy, indent=2))
        print(f"\n  ✅ 策略生成成功")
        return 0
    except Exception as e:
        print(f"\n  ❌ 调用失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Stage 5: UV 展开与打包

输入: stage4_low_passed.obj + strategy.json
输出: stage5_low_uv.fbx

流程:
  1. 导入低模到 Blender 无头
  2. 基于硬边/材质 ID 自动标记接缝
  3. UV 展开（Smart UV Project）
  4. UVPackmaster 紧密打包
  5. 可选: 生成光照贴图第二套 UV
"""

from typing import Optional


def run(low_poly_path: str, strategy: dict) -> Optional[str]:
    """执行 Stage 5 UV 展开。

    Args:
        low_poly_path: 通过 Gate A 的低模路径
        strategy: 处理策略（含 UV 分辨率等参数）

    Returns:
        带 UV 的 FBX 路径，失败返回 None
    """
    uv_res = strategy.get("uv_resolution", 2048)
    print(f"[Stage 5] UV 展开: {low_poly_path}, 分辨率={uv_res}")

    # TODO: Blender 无头脚本: 导入 → 标记接缝 → UV 展开 → UVPackmaster 打包
    # TODO: 光照贴图 UV 生成

    output_path = "./output/stage5_low_uv.fbx"
    print(f"[Stage 5] 输出带 UV 低模: {output_path}")
    return output_path

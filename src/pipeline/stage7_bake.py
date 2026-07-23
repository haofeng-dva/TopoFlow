"""Stage 7: 烘焙贴图

输入: stage5_low_uv.fbx + stage0_raw.obj
输出: 法线贴图 / AO / 曲率贴图

流程:
  1. Blender 无头 Cycles 烘焙
  2. 法线贴图（切线空间，可配置 DX/GL）
  3. 环境光遮蔽（AO）
  4. 曲率贴图
  5. 可选: 厚度/空腔/材质 ID
"""

# dict is a builtin in Python 3.9+


def run(low_poly_uv_path: str, high_poly_path: str, strategy: dict) -> dict:
    """执行 Stage 7 贴图烘焙。

    Args:
        low_poly_uv_path: 带 UV 的低模路径
        high_poly_path: 高模（脏模）路径
        strategy: 处理策略（含烘焙分辨率、法线空间等）

    Returns:
        贴图路径字典: {normal, ao, curvature, ...}
    """
    bake_res = strategy.get("bake_resolution", 2048)
    normal_space = strategy.get("normal_space", "directx")
    print(f"[Stage 7] 烘焙贴图: {bake_res}, {normal_space}")

    # TODO: Blender 无头 Cycles 烘焙脚本
    # TODO: cage 自动生成
    # TODO: 法线贴图（DX/GL 可选）
    # TODO: AO 贴图
    # TODO: 曲率贴图

    maps = {
        "normal": f"./output/maps/normal_{'dx' if normal_space == 'directx' else 'gl'}.png",
        "ao": "./output/maps/ao.png",
        "curvature": "./output/maps/curvature.png",
    }

    print(f"[Stage 7] 贴图完成")
    return maps

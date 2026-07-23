"""Stage 0: 设计图 → 脏模型（AI 自动建模）

输入: 设计图路径 (PNG/JPG)
输出: stage0_raw.obj（脏模/高模）

流程:
  1. LLM 分析图像 → 生成 API 参数 JSON
  2. 参数 Schema 校验 → 非法则回退默认参数
  3. 缓存命中检查（图像 hash + 参数）
  4. 调用 Meshy Image-to-3D API（失败重试 1 次，切换备选 API）
  5. 完整性校验（非空、面数合理）
  6. 下载并输出 OBJ
"""

from typing import Optional


def run(image_path: str, config: dict) -> Optional[str]:
    """执行 Stage 0。

    Args:
        image_path: 输入设计图路径
        config: 全局配置（含 API keys、预设参数）

    Returns:
        生成的脏模型 OBJ 路径，失败返回 None
    """
    print(f"[Stage 0] 处理设计图: {image_path}")

    # TODO: LLM 图像分析 → 生成参数 JSON
    # TODO: Schema 校验
    # TODO: 缓存检查
    # TODO: 调用 Meshy API / TripoSR
    # TODO: 完整性校验
    # TODO: 输出 stage0_raw.obj

    output_path = "./output/stage0_raw.obj"
    print(f"[Stage 0] 输出脏模型: {output_path}")
    return output_path

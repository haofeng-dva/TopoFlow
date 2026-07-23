"""Stage 2: 用户确认策略（人工干预点）

输入: strategy.json / diagnosis_report.json
输出: 用户确认或修改后的策略

流程:
  1. 展示策略摘要给用户
  2. 用户可选：一键确认 / 修改参数 / 上传引导曲线 / 上传冻结遮罩
  3. Auto-pilot 模式自动跳过
"""


def run(strategy: dict, diagnosis: dict, auto_pilot: bool = False) -> dict:
    """执行 Stage 2。

    Args:
        strategy: LLM 生成的策略 JSON
        diagnosis: 诊断报告
        auto_pilot: 是否自动跳过人工确认

    Returns:
        用户确认后的策略字典
    """
    if auto_pilot and strategy.get("auto_pilot_eligible", False):
        print(f"[Stage 2] Auto-pilot 模式，自动跳过")
        return strategy

    print(f"[Stage 2] 等待用户确认策略...")
    # TODO: 通过 Web UI 展示策略，接收用户修改
    # TODO: 处理引导曲线上传
    # TODO: 处理冻结遮罩上传

    print(f"[Stage 2] 策略已确认")
    return strategy

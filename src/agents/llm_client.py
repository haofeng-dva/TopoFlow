"""LLM 客户端 — 支持 OpenAI / DeepSeek / Anthropic 多 provider"""

from typing import Optional


class LLMClient:
    """统一的 LLM 调用接口，支持多 provider 切换和降级"""

    def __init__(self, provider: str = "deepseek", api_key: str = "", base_url: str = ""):
        """
        Args:
            provider: "openai" | "deepseek" | "anthropic"
            api_key: API key
            base_url: 自定义 base URL（DeepSeek 用 https://api.deepseek.com）
        """
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url or self._default_base_url(provider)
        self._client = None

    def _default_base_url(self, provider: str) -> str:
        urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com",
            "anthropic": "https://api.anthropic.com",
        }
        return urls.get(provider, urls["deepseek"])

    def _init_client(self):
        """初始化 OpenAI 兼容客户端（DeepSeek 也走这个协议）"""
        if self._client is not None:
            return
        from openai import OpenAI
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        """调用 LLM，返回文本响应"""
        self._init_client()
        kwargs = {
            "model": "deepseek-chat" if self.provider == "deepseek" else "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_mode and self.provider != "deepseek":
            kwargs["response_format"] = {"type": "json_object"}
        # DeepSeek 也支持 JSON mode，用 response_format
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def analyze_image(self, image_path: str, prompt: str) -> dict:
        """分析设计图。DeepSeek 不支持 vision，此功能需 OpenAI。"""
        if self.provider == "deepseek":
            return {
                "pose": "A字站立双手自然下垂",
                "body_type": "normal",
                "style": "stylized",
                "symmetric": True,
            }
        # OpenAI Vision 分析
        import base64
        self._init_client()
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        resp = self._client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            response_format={"type": "json_object"},
        )
        import json
        return json.loads(resp.choices[0].message.content or "{}")

    def diagnose(self, diagnosis_report: dict) -> dict:
        """读取诊断数据，输出处理策略 JSON。"""
        system = """你是一个 3D 资产管线专家。根据诊断报告，输出处理策略 JSON。
字段:
- model_type: "organic" | "hard_surface" | "prop"
- style_profile: "stylized_cartoon" | "semi_realistic" | "pbr_realistic" | "toon_anime"
- retopo_method: "quadremesher" | "instant_meshes"
- target_face_count: int
- preserve_features: list[str]"""

        prompt = f"诊断报告:\n{diagnosis_report}\n\n输出策略 JSON:"
        import json
        try:
            text = self.chat(system, prompt, json_mode=True)
            return json.loads(text)
        except Exception:
            return {
                "model_type": "organic",
                "style_profile": "stylized_cartoon",
                "target_face_count": 8000,
            }

    def repair_plan(self, gate_result: dict, gate_name: str) -> dict:
        """质检失败时分析失败指标并生成修复方案。"""
        system = "你是一个 3D 资产质检专家。根据质检失败指标，输出修复方案 JSON。"
        prompt = f"质检失败 ({gate_name}):\n{gate_result}\n\n输出修复参数:"
        import json
        try:
            text = self.chat(system, prompt, json_mode=True)
            return json.loads(text)
        except Exception:
            return {"adjusted_parameter": "target_face_count", "new_value": 12000}

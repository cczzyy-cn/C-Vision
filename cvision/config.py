"""读取运行时配置（DeepSeek API key、端点、视觉模型）。"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# 允许从项目根 .env 加载配置
load_dotenv()

# 默认值（DeepSeek OpenAI 兼容端点）
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_VISION_MODEL = "deepseek-v4-flash-vision-exp"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip()
DEEPSEEK_VISION_MODEL = os.environ.get("DEEPSEEK_VISION_MODEL", DEFAULT_VISION_MODEL).strip()


class ConfigError(RuntimeError):
    """配置缺失或非法。"""


def require_api_key() -> str:
    """返回 API key，缺失时抛出 ConfigError。"""
    if not DEEPSEEK_API_KEY:
        raise ConfigError(
            "未设置 DEEPSEEK_API_KEY。请在 .env 中填写，或通过环境变量注入。"
        )
    return DEEPSEEK_API_KEY


def chat_endpoint() -> str:
    """拼接 OpenAI 兼容的 /chat/completions 端点。"""
    base = DEEPSEEK_BASE_URL.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"

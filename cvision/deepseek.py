"""DeepSeek 视觉模型调用：向 ``deepseek-v4-flash-vision-exp`` 发送图片并返回文本。

使用 OpenAI 兼容的 ``/chat/completions`` 端点，图片以 ``data:image/*;base64,`` 形式
放入 user 消息的 ``image_url`` 内容块。
"""

from __future__ import annotations

import requests

from cvision.config import DEEPSEEK_VISION_MODEL, chat_endpoint, require_api_key

# 允许的 detail 取值（对应 DeepSeek 视觉文档）
ALLOWED_DETAILS = ("low", "high", "original", "auto")

DEFAULT_PROMPT = "请描述这张图片的内容。"


def analyze_image(
    image_data_url: str,
    *,
    prompt: str = DEFAULT_PROMPT,
    detail: str = "auto",
    model: str | None = None,
    timeout: int = 120,
) -> str:
    """向视觉模型发送一张图片 data URL，返回模型的文本回答。

    参数:
        image_data_url: ``data:<mime>;base64,<data>`` 形式的图片。
        prompt: 对图片的提问/指令。
        detail: ``low`` / ``high`` / ``original`` / ``auto``。
        model: 视觉模型名，默认取配置。
        timeout: 请求超时（秒）。

    异常:
        ConfigError: 未配置 DEEPSEEK_API_KEY。
        requests.HTTPError: DeepSeek 返回非 2xx（携带响应体）。
        KeyError / IndexError: 响应结构异常。
    """
    if detail not in ALLOWED_DETAILS:
        raise ValueError(f"detail 必须是 {ALLOWED_DETAILS} 之一，收到 {detail!r}")

    api_key = require_api_key()
    model = model or DEEPSEEK_VISION_MODEL

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url, "detail": detail},
                    },
                ],
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    resp = requests.post(chat_endpoint(), json=payload, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise requests.HTTPError(
            f"DeepSeek 请求失败 status={resp.status_code}: {resp.text}",
            response=resp,
        )

    data = resp.json()
    return data["choices"][0]["message"]["content"]

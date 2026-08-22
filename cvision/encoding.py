"""图片编码：PIL Image -> base64 data URL，供 DeepSeek 视觉请求使用。"""

from __future__ import annotations

import base64
import io

from PIL import Image

# 支持的图片格式 -> data URL MIME 类型
_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "WEBP": "image/webp",
}

_DEFAULT_FORMAT = "JPEG"


def image_to_base64(img: Image.Image, format: str = _DEFAULT_FORMAT) -> tuple[str, str]:
    """将 PIL 图片编码为 base64。

    返回 ``(mime_type, base64_str)``。默认 JPEG；含透明通道时建议使用 PNG。
    """
    fmt = (format or _DEFAULT_FORMAT).upper()
    mime = _MIME.get(fmt)
    if mime is None:
        raise ValueError(f"不支持的图片格式 {fmt!r}，可选：{', '.join(_MIME)}")

    buf = io.BytesIO()
    img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return mime, b64


def image_to_data_url(img: Image.Image, format: str = _DEFAULT_FORMAT) -> str:
    """将 PIL 图片编码为 ``data:<mime>;base64,<data>`` 形式的 data URL。"""
    mime, b64 = image_to_base64(img, format=format)
    return f"data:{mime};base64,{b64}"

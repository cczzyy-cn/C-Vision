"""C-Vision MCP Server：为 AI 智能体提供屏幕/窗口视觉能力。

启动方式（stdio，供智能体拉起）：:

    python -m cvision.server

核心工具是 ``see``：截取窗口或全屏 → 转 Base64 → 交给 ``deepseek-v4-flash-vision-exp``
分析并返回文本。``list_windows`` 用于让智能体"搜索"目标窗口，``analyze_image`` 用于
分析智能体手里已有的图片。

环境变量:
    DEEPSEEK_API_KEY    必须，DeepSeek API Key。
    DEEPSEEK_BASE_URL   可选，默认 https://api.deepseek.com。
    DEEPSEEK_VISION_MODEL  可选，默认 deepseek-v4-flash-vision-exp。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import cvision.capturer as capturer
import cvision.deepseek as deepseek
import cvision.encoding as encoding

mcp = FastMCP("c-vision")


def _to_bool(value) -> bool:
    """把 MCP 传入的 bool/字符串归一化为布尔。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y")
    return bool(value)


@mcp.tool()
def list_windows() -> list[dict]:
    """列出当前可见的顶层 Windows 窗口。

    用于让智能体"搜索"目标软件窗口：每个窗口包含 handle / title / left / top /
    width / height。把结果里的 handle 或 title 子串传给 ``see`` 即可分析该窗口。

    返回:
        窗口字典列表，按屏幕上从左到右、从上到下排序。
    """
    return [w.to_dict() for w in capturer.list_windows()]


@mcp.tool()
def see(
    handle: int | None = None,
    title_substr: str | None = None,
    prompt: str = deepseek.DEFAULT_PROMPT,
    detail: str = "auto",
    maximize: bool = False,
) -> str:
    """看屏幕或某个窗口，返回 DeepSeek 视觉模型的分析文本。

    C-Vision 的核心工具：截屏（窗口或全屏）→ 转 Base64 → 交给
    ``deepseek-v4-flash-vision-exp`` → 返回模型回答。

    参数:
        handle: 窗口句柄（来自 list_windows）。优先于 title_substr。
        title_substr: 窗口标题子串（忽略大小写），用于按名称查找窗口。
        prompt: 对画面的提问/指令，例如"识别截图中的文字"、"描述这张图"、
            "读取图表数据"。
        detail: ``low``(缩放到512x512,省token) / ``high`` / ``original`` /
            ``auto``。
        maximize: 为 True 时先最大化目标窗口再截屏（对最小化/后台窗口有效）。

    返回:
        模型对画面的文本回答。未传 handle/title_substr 时分析整个屏幕。
    """
    maximize = _to_bool(maximize)
    if maximize and handle is None and not title_substr:
        raise ValueError("maximize=True 时需要 handle 或 title_substr 指定窗口")
    if handle is not None or title_substr:
        img = capturer.capture_window(handle=handle, title_substr=title_substr, maximize=maximize)
    else:
        img = capturer.capture_screen()
    url = encoding.image_to_data_url(img)
    return deepseek.analyze_image(url, prompt=prompt, detail=detail)


@mcp.tool()
def analyze_image(
    image_data_url: str,
    prompt: str = deepseek.DEFAULT_PROMPT,
    detail: str = "auto",
) -> str:
    """分析一张已编码为 Base64 data URL 的图片，返回文本。

    当智能体手里已有图片（例如其他工具返回的 ``data:image/...;base64,...``），
    可直接交给本工具分析；也可用 ``see`` 直接看屏幕/窗口。

    参数:
        image_data_url: ``data:<mime>;base64,<data>`` 形式的图片。
        prompt: 对图片的提问/指令。
        detail: ``low`` / ``high`` / ``original`` / ``auto``。

    返回:
        模型对图片的文本回答。
    """
    return deepseek.analyze_image(image_data_url, prompt=prompt, detail=detail)


@mcp.tool()
def screenshot(
    handle: int | None = None,
    title_substr: str | None = None,
    maximize: bool = False,
    format: str = "JPEG",
) -> str:
    """截取整个屏幕或指定窗口，返回 Base64 data URL（不调用视觉模型）。

    与 ``see`` 的区别：本工具只返回原始截图数据，供智能体保存、转发或交给其他
    处理；``see`` 则会进一步把截图交给视觉模型并返回文本分析。

    参数:
        handle: 窗口句柄（来自 list_windows）。优先于 title_substr。
        title_substr: 窗口标题子串（忽略大小写），用于按名称查找窗口。
        maximize: 为 True 时先最大化目标窗口再截图（对最小化/后台窗口有效）。
        format: 图片编码格式，``JPEG`` / ``PNG`` / ``WEBP`` / ``GIF``，默认 JPEG。

    返回:
        ``data:<mime>;base64,<data>`` 形式的图片。未传窗口参数时截取整个屏幕。
    """
    maximize = _to_bool(maximize)
    if maximize and handle is None and not title_substr:
        raise ValueError("maximize=True 时需要 handle 或 title_substr 指定窗口")
    if handle is not None or title_substr:
        img = capturer.capture_window(handle=handle, title_substr=title_substr, maximize=maximize)
    else:
        img = capturer.capture_screen()
    return encoding.image_to_data_url(img, format=format)


# 图片格式 -> 文件扩展名
_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}


def _save_capture(img, fmt: str = "PNG", save_to: str | None = None) -> str:
    """把 PIL 图片保存为本地文件，返回绝对路径。"""
    fmt = (fmt or "PNG").upper()
    ext = _EXT.get(fmt)
    if ext is None:
        raise ValueError(f"不支持的图片格式 {fmt!r}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    name = f"cvision_{ts}.{ext}"
    if save_to:
        p = Path(save_to)
        if p.suffix.lower() in ("".join("." + e for e in _EXT.values()), ".jpeg"):
            path = p
        else:
            p.mkdir(parents=True, exist_ok=True)
            path = p / name
    else:
        base = Path(__file__).resolve().parent.parent / "captures"
        base.mkdir(parents=True, exist_ok=True)
        path = base / name
    img.save(path, format=fmt)
    return str(path.resolve())


@mcp.tool()
def screenshot_file(
    handle: int | None = None,
    title_substr: str | None = None,
    maximize: bool = False,
    format: str = "PNG",
    save_to: str | None = None,
) -> str:
    """截取整个屏幕或指定窗口，保存为本地图像文件，返回文件路径。

    与 ``screenshot``（返回 Base64 文本）不同，本工具把截图**落盘为文件**并返回
    绝对路径。得到的路径用 ``@<path>`` 引用，Reasonix 就会把该图作为官方视觉
    输入（inline base64）发给视觉模型，从而让模型真正"看到"这张截图。

    参数:
        handle: 窗口句柄（来自 list_windows）。优先于 title_substr。
        title_substr: 窗口标题子串（忽略大小写），用于按名称查找窗口。
        maximize: 为 True 时先最大化目标窗口再截图（截图后还原原状态）。
        format: 图片编码格式，``PNG`` / ``JPEG`` / ``WEBP`` / ``GIF``，默认 PNG。
        save_to: 保存路径。可指定完整文件路径，或一个目录（自动加时间戳文件名）；
            留空则保存到项目根 ``captures/`` 目录。

    返回:
        保存后的文件绝对路径。
    """
    maximize = _to_bool(maximize)
    if maximize and handle is None and not title_substr:
        raise ValueError("maximize=True 时需要 handle 或 title_substr 指定窗口")
    if handle is not None or title_substr:
        img = capturer.capture_window(handle=handle, title_substr=title_substr, maximize=maximize)
    else:
        img = capturer.capture_screen()
    return _save_capture(img, fmt=format, save_to=save_to)


if __name__ == "__main__":
    mcp.run()

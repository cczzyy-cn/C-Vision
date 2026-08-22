"""窗口图像/类名的纯逻辑判定（不依赖 win32，仅依赖 PIL）。

只放不碰 win32 的判定函数，供 ``capturer`` 复用，也便于在任意平台（含 Linux CI）
上跑 Python 单元测试。
"""

from __future__ import annotations

from PIL import Image

# 已知用 GPU/合成渲染、PrintWindow 抓不到（或只抓到部分帧）的窗口类名前缀。
GPU_WINDOW_CLASS_PREFIXES = (
    "OrpheusBrowserHost",   # 网易云音乐（Chromium 宿主）
    "Chrome_WidgetWin",     # Chrome/Electron
    "Electron",
    "CefBrowserWindow",     # CEF
    "ApplicationFrameWindow",  # UWP/WinUI
    "Qt",                   # Qt 部分版本用合成渲染
    "UnityWndClass",        # Unity 游戏窗口
)


def looks_like_gpu_class(classname: str) -> bool:
    """按窗口类名判断是否属于 GPU/合成渲染窗口（PrintWindow 不可靠）。"""
    name = (classname or "").strip()
    if not name:
        return False
    return any(name.startswith(p) for p in GPU_WINDOW_CLASS_PREFIXES)


def is_blank_image(img: Image.Image, max_std: float = 2.0, dominant_ratio: float = 0.98) -> bool:
    """判断画面是否几乎为纯色/空白（含"少数像素有内容"的部分空白帧）。

    背景：``PrintWindow`` 对 GPU 合成窗口（Chromium/Electron 等）常"成功"返回：
    - 一张纯白/纯黑空帧（标准差极小）；
    - 或只渲染出边框/标题栏，主体仍是空的"部分空白帧"（方差被小区域拉高，仅靠
      方差判不出来）。

    因此用两条判定：
    1. 灰度方差足够小（接近纯色）；
    2. 或绝大多数像素落在某个窄亮度带内（主色覆盖占比 ≥ dominant_ratio，
       即内容像素极少）。

    命中任一即视为空白，从而触发回退。
    """
    if img is None:
        return True
    try:
        hist = img.convert("L").resize((64, 64)).histogram()  # 256 bin
        total = sum(hist)
        if total == 0:
            return False
        mean = sum(i * hist[i] for i in range(256)) / total
        var = sum(((i - mean) ** 2) * hist[i] for i in range(256)) / total
        if var < max_std * max_std:
            return True

        # 主色覆盖：某亮度带（±16）内的像素占比
        band_lo = max(0, int(mean) - 16)
        band_hi = min(255, int(mean) + 16)
        band_count = sum(hist[i] for i in range(band_lo, band_hi + 1))
        return band_count / total >= dominant_ratio
    except Exception:
        return False

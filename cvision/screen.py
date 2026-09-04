"""显示器/DPI 信息：供模型了解屏幕布局与缩放，避免高 DPI 下坐标误判。

返回结构（平台无关）::

    [
      {"index": 0, "x": int, "y": int, "width": int, "height": int,
       "primary": bool, "scale": float},
      ...
    ]

- Windows：``EnumDisplayMonitors`` + ``GetMonitorInfo``（bounds）+ ``GetDpiForMonitor``（scale）。
- macOS：``Quartz.CGGetActiveDisplayList`` + ``CGDisplayBounds``。
- Linux：回退到 PIL 全屏尺寸（单屏，scale=1）。

任何平台探测失败都会回退到「单屏 = 全屏尺寸」，保证调用方总能拿到可用的布局。
"""

from __future__ import annotations

import sys

from PIL import Image, ImageGrab


def _monitors_windows() -> list[dict]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    shcore = ctypes.windll.shcore

    monitors: list[dict] = []

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_ulong,  # HMONITOR
        ctypes.c_ulong,  # HDC
        ctypes.c_void_p,  # LPRECT
        ctypes.c_long,  # LPARAM
    )

    def _monitor_info(hmon) -> dict | None:
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(wintypes.HMONITOR(hmon), ctypes.byref(info)):
            return None
        r = info.rcMonitor
        # 每显示器 DPI（同一屏幕内有多个 scale 时取主 scale）
        scale = 1.0
        try:
            dpi_x = ctypes.c_uint()
            dpi_y = ctypes.c_uint()
            shcore.GetDpiForMonitor(
                wintypes.HMONITOR(hmon), 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
            )  # MDT_EFFECTIVE_DPI
            scale = dpi_x.value / 96.0
        except Exception:
            pass
        return {
            "x": int(r.left),
            "y": int(r.top),
            "width": int(r.right - r.left),
            "height": int(r.bottom - r.top),
            "scale": round(scale, 2),
        }

    def _cb(hmon, _hdc, _lprect, _lparam):
        m = _monitor_info(hmon)
        if m is not None:
            monitors.append(m)
        return 1

    try:
        user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_cb), 0)
    except Exception:
        monitors = []

    if not monitors:
        return []

    # 以包含 (0,0) 的显示器为主屏（Windows 主屏通常原点在 (0,0)）。
    primary_index = 0
    for i, m in enumerate(monitors):
        if m["x"] <= 0 <= m["x"] + m["width"] and m["y"] <= 0 <= m["y"] + m["height"]:
            primary_index = i
            break
    for i, m in enumerate(monitors):
        m["index"] = i
        m["primary"] = i == primary_index
    return monitors


def _monitors_macos() -> list[dict]:
    import Quartz

    ids = Quartz.CGGetActiveDisplayList(16, None, None)
    displays: list[dict] = []
    count = int(ids[0]) if ids else 0
    for i in range(min(count, 16)):
        d = int(ids[1][i])
        bounds = Quartz.CGDisplayBounds(d)
        displays.append(
            {
                "index": i,
                "x": int(bounds.origin.x),
                "y": int(bounds.origin.y),
                "width": int(bounds.size.width),
                "height": int(bounds.size.height),
                "primary": bool(Quartz.CGDisplayIsMain(d)),
                "scale": 1.0,
            }
        )
    return displays


def screen_info() -> list[dict]:
    """返回显示器/DPI 布局列表（平台相关探测 + 兜底）。"""
    try:
        if sys.platform.startswith("win"):
            return _monitors_windows()
        if sys.platform == "darwin":
            return _monitors_macos()
    except Exception:
        pass

    # 兜底：单屏 = 全屏尺寸（PIL；无显示环境时给空值，避免抛错）。
    try:
        img = ImageGrab.grab()
        width, height = img.width, img.height
    except Exception:
        width, height = 0, 0
    return [
        {
            "index": 0,
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "primary": True,
            "scale": 1.0,
        }
    ]

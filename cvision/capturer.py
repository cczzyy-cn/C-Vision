"""兼容层：``cvision.capturer`` 转发到平台捕获后端（``cvision.capture``）。

保留旧导入路径（``from cvision import capturer``）可用；实际实现按平台分发到
``cvision.capture.windows / macos / linux``。
"""

from __future__ import annotations

from cvision.capture import list_windows, capture_window, capture_screen, Window
from cvision.capture.base import CaptureBackend

__all__ = [
    "Window",
    "CaptureBackend",
    "list_windows",
    "capture_window",
    "capture_screen",
]

"""捕获层门面：按 ``sys.platform`` 选择后端，统一暴露窗口/屏幕捕获。

后端模块：``windows`` / ``macos`` / ``linux``（各提供
``list_windows`` / ``capture_window`` / ``capture_screen``）。
``Window`` 来自 ``cvision.capture.base``，平台无关。
"""

from __future__ import annotations

import sys

from .base import CaptureBackend, Window  # noqa: F401  (CaptureBackend 供类型标注)


def _select_backend():
    platform = sys.platform
    if platform.startswith("win"):
        from . import windows
        return windows
    if platform == "darwin":
        from . import macos
        return macos
    from . import linux
    return linux


backend = _select_backend()
list_windows = backend.list_windows
capture_window = backend.capture_window
capture_screen = backend.capture_screen

__all__ = [
    "Window",
    "CaptureBackend",
    "list_windows",
    "capture_window",
    "capture_screen",
]

"""Linux 屏幕/窗口捕获后端（Phase 2：尚未实现）。

Phase 1 只搭好门面 + Windows/macOS 后端；Linux 这一步先用占位，保证
``import cvision.capture`` 在 Linux 上可导入，调用时给出明确的未实现提示。
X11 计划用 ``python-xlib``（``_NET_CLIENT_LIST`` 枚举 + XComposite 抓窗口），
Wayland 走 ``xdg-desktop-portal``。见 README 的多平台方案。
"""

from __future__ import annotations

from cvision.capture.base import Window

_NOT_IMPLEMENTED = (
    "Linux 后端尚未实现（Phase 2）。计划：X11 用 python-xlib + XComposite 抓窗口、"
    "mss 抓整屏；Wayland 走 xdg-desktop-portal。"
)


def list_windows() -> list[Window]:
    raise NotImplementedError(_NOT_IMPLEMENTED)


def capture_window(
    handle: int | None = None,
    title_substr: str | None = None,
    maximize: bool = False,
):
    raise NotImplementedError(_NOT_IMPLEMENTED)


def capture_screen():
    raise NotImplementedError(_NOT_IMPLEMENTED)

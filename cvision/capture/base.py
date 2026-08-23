"""平台无关的捕获抽象：Window 数据类 + 后端协议。

每个平台后端（windows / macos / linux）提供同样的三个函数：
    - list_windows() -> list[Window]
    - capture_window(handle=None, title_substr=None, maximize=False) -> Image.Image
    - capture_screen() -> Image.Image
门面 ``cvision.capture`` 按 ``sys.platform`` 选择后端并重新导出。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class Window:
    """描述一个可见顶层窗口（平台无关）。

    ``handle`` 是平台窗口ID：Windows 的 HWND / macOS 的 CGWindowID / X11 的 window id。
    """

    handle: int
    title: str
    left: int
    top: int
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "handle": self.handle,
            "title": self.title,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


class CaptureBackend(ABC):
    """一个平台后端的统一接口。"""

    @abstractmethod
    def list_windows(self) -> list[Window]:
        ...

    @abstractmethod
    def capture_window(
        self,
        handle: int | None = None,
        title_substr: str | None = None,
        maximize: bool = False,
    ) -> Image.Image:
        ...

    @abstractmethod
    def capture_screen(self) -> Image.Image:
        ...

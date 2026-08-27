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


def pick_window(windows: list["Window"], title_substr: str | None) -> "Window | None":
    """在所有可见窗口里挑选最匹配 ``title_substr`` 的一个，统一各入口的窗口定位语义。

    匹配优先级（均为子串命中时）：
    1. **精确标题匹配** 优先于子串匹配——避免 ``see(window="微信")`` 误中标题里含
       “微信”的浏览器标签（微信主窗标题恰为“微信”）；
    2. 同精度下优先**非最小化/有内容**的窗口（Windows 最小化窗口坐标是负占位值）；
    3. 再优先面积更大的窗口。

    返回 ``Window`` 或 ``None``（无命中）。纯逻辑、不依赖 win32，可跨平台单测。
    """
    if not title_substr:
        return None
    needle = title_substr.strip().lower()
    if not needle:
        return None

    def _is_minimized(w: "Window") -> bool:
        # Windows 最小化窗口的 GetWindowRect 是 (-32000,-32000,160,28) 占位值
        return bool(w.left < 0 and w.top < 0)

    def key(w: "Window"):
        title = (w.title or "").lower()
        exact = 0 if title == needle else 1
        sub = 0 if needle in title else 1
        return (exact, sub, 1 if _is_minimized(w) else 0, -(max(1, w.width) * max(1, w.height)))

    matches = [w for w in windows if needle in (w.title or "").lower()]
    if not matches:
        return None
    return min(matches, key=key)


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

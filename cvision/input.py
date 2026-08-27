"""用户级输入：模拟真人操作（鼠标点击/移动/滚动、键盘输入/快捷键、窗口聚焦）。

跨平台用 ``pyautogui``（需本机有显示）；窗口聚焦在 Windows 用 pywin32 置前。
所有函数都直接作用于**当前桌面**，被调用前请先 ``see`` 确认目标。
"""

from __future__ import annotations

import sys
import time

# 常见按键名 -> pyautogui 键名
_KEY_ALIASES = {
    "enter": "enter", "return": "enter", "tab": "tab", "esc": "esc", "escape": "esc",
    "space": "space", "backspace": "backspace", "delete": "delete", "del": "delete",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end", "pageup": "pageup", "pagedown": "pagedown",
    "ctrl": "ctrl", "control": "ctrl", "shift": "shift", "alt": "alt", "win": "win",
    "cmd": "win", "meta": "win",
}
for _i in range(1, 13):
    _KEY_ALIASES[f"f{_i}"] = f"f{_i}"


def _require_pyautogui():
    try:
        import pyautogui  # noqa: F401
        return pyautogui
    except ImportError:
        raise RuntimeError("需要 pyautogui：python -m pip install pyautogui（并确保有桌面环境/显示）")


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _parse_keys(keys: str) -> tuple[list[str], str]:
    """解析 ``ctrl+shift+t`` 之类的组合，返回 (修饰键列表, 主键)。"""
    parts = [p.strip().lower() for p in keys.replace(" ", "").split("+") if p.strip()]
    mods, main = parts[:-1], parts[-1]
    main = _KEY_ALIASES.get(main, main)
    mods = [_KEY_ALIASES.get(m, m) for m in mods]
    return mods, main


def focus_window(title_substr: str | None = None, handle: int | None = None) -> int | None:
    """把窗口置前：优先按 ``handle`` 精确定位，否则按标题（精确标题优先，其次子串）。

    Windows 用 pywin32；仅 Windows 支持。返回最终置前的窗口句柄。
    """
    if not _is_windows():
        raise RuntimeError("focus_window 仅在 Windows 上支持（依赖 pywin32）")
    import win32con
    import win32gui

    if handle is None:
        if not title_substr:
            raise ValueError("focus_window 需要 handle 或 title_substr 之一")
        # 统一走 capture 层挑选：精确标题优先，避免“微信”误中标题含它的浏览器标签
        from cvision.capture import list_windows, pick_window

        win = pick_window(list_windows(), title_substr)
        if win is None:
            raise LookupError(f"未找到标题含 {title_substr!r} 的窗口")
        handle = win.handle

    hwnd = int(handle)
    if not win32gui.IsWindow(hwnd):
        raise LookupError(f"无效窗口句柄 {handle}")
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # 最小化了先还原
    except Exception:
        pass
    try:
        win32gui.SetForegroundWindow(hwnd)
        win32gui.BringWindowToTop(hwnd)
    except Exception:
        pass
    time.sleep(0.2)
    return hwnd


def move(x: int, y: int) -> None:
    _require_pyautogui().moveTo(x, y, duration=0.1)


def click(x: int, y: int, button: str = "left", double: bool = False) -> None:
    pg = _require_pyautogui()
    if double:
        pg.doubleClick(x, y, button=button)
    else:
        pg.click(x, y, button=button)


def scroll(x: int, y: int, dx: int = 0, dy: int = 0) -> None:
    pg = _require_pyautogui()
    pg.moveTo(x, y, duration=0.05)
    # pyautogui.scroll(正数)=向上滚，负数=向下滚。dy>0 约定为“向上滚”，故直接传 dy。
    if dy:
        pg.scroll(dy, x, y)
    if dx and hasattr(pg, "hscroll"):
        pg.hscroll(dx, x, y)


def _paste_clipboard(text: str) -> None:
    """用剪贴板 + Ctrl+V 输入非 ASCII 文本（pyautogui.write 打不进中文等）。"""
    try:
        import win32clipboard
        import win32con
    except ImportError as e:  # pragma: no cover - 仅当未装 pywin32
        raise RuntimeError("输入非 ASCII 文本需要 pywin32（Windows）：pip install pywin32") from e
    old = None
    try:  # 备份旧剪贴板文本
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            old = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except Exception:
        old = None
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()
    time.sleep(0.05)
    _require_pyautogui().hotkey("ctrl", "v")
    if old is not None:  # 尽力恢复剪贴板
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old)
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def type_text(text: str) -> None:
    pg = _require_pyautogui()
    if text.isascii():
        pg.write(text, interval=0.03)
        return
    _paste_clipboard(text)


def press_keys(keys: str) -> None:
    """发送快捷键/按键，如 ``ctrl+l``、``enter``、``ctrl+shift+t``。"""
    pg = _require_pyautogui()
    mods, main = _parse_keys(keys)
    if mods:
        pg.hotkey(*(mods + [main]))
    else:
        pg.press(main)


# 供 CLI/测试判断能力
CAPABILITIES = ["click", "double_click", "move", "scroll", "type_text", "press_keys", "focus_window"]

"""用户级输入：模拟真人操作（鼠标点击/移动/滚动、键盘输入/快捷键、窗口聚焦）。

跨平台用 ``pyautogui``（需本机有显示）；窗口聚焦在 Windows 用 pywin32 置前。
所有函数都直接作用于**当前桌面**，被调用前请先 ``see`` 确认目标。
"""

from __future__ import annotations

import ctypes
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


def _parse_keys(keys: str) -> tuple[list[str], str]:
    """解析 ``ctrl+shift+t`` 之类的组合，返回 (修饰键列表, 主键)。"""
    parts = [p.strip().lower() for p in keys.replace(" ", "").split("+") if p.strip()]
    mods, main = parts[:-1], parts[-1]
    main = _KEY_ALIASES.get(main, main)
    mods = [ _KEY_ALIASES.get(m, m) for m in mods ]
    return mods, main


def focus_window(title_substr: str) -> None:
    """把标题含子串的窗口置前（Windows 用 pywin32；其它平台不保证）。"""
    import win32con
    import win32gui

    needle = title_substr.strip().lower()
    target = None

    def _enum(hwnd, _):
        nonlocal target
        if not win32gui.IsWindowVisible(hwnd):
            return
        if needle in win32gui.GetWindowText(hwnd).lower():
            target = hwnd
            return

    win32gui.EnumWindows(_enum, 0)
    if target is None:
        raise LookupError(f"未找到标题含 {title_substr!r} 的窗口")
    try:
        win32gui.ShowWindow(target, win32con.SW_RESTORE)  # 最小化了先还原
    except Exception:
        pass
    try:
        win32gui.SetForegroundWindow(target)
        win32gui.BringWindowToTop(target)
    except Exception:
        pass
    time.sleep(0.2)


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
    if dy:
        pg.scroll(-dy, x, y)  # 正 di 向上滚
    if dx:
        pg.hscroll(dx, x, y) if hasattr(pg, "hscroll") else None


def type_text(text: str) -> None:
    pg = _require_pyautogui()
    pg.write(text, interval=0.03)


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

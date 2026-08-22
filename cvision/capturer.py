"""Windows 屏幕/窗口捕获：枚举可见顶层窗口、抓取窗口或全屏。

依赖 pywin32 + Pillow。窗口捕获优先使用 ``PrintWindow(PW_RENDERFULLCONTENT)``，
可以抓取被遮挡/非前台窗口的画面；失败时回退到整屏 ``ImageGrab`` 裁剪窗口矩形。
"""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass

import win32con
import win32gui
import win32ui
from PIL import Image, ImageGrab

# PrintWindow 的 PW_RENDERFULLCONTENT（Win 8.1+），可捕获前台之外窗口内容
_PW_RENDERFULLCONTENT = 2

# 已知用 GPU/合成渲染、PrintWindow 抓不到（或只抓到部分帧）的窗口类名前缀。
# 命中这些类名时直接绕过 PrintWindow，走"读合成桌面区域"路径。
_GPU_WINDOW_CLASS_PREFIXES = (
    "OrpheusBrowserHost",   # 网易云音乐（Chromium 宿主）
    "Chrome_WidgetWin",     # Chrome/Electron
    "Electron",
    "CefBrowserWindow",     # CEF
    "ApplicationFrameWindow",  # UWP/WinUI
    "Qt",                   # Qt 部分版本用合成渲染
    "UnityWndClass",        # Unity 游戏窗口
)
_WS_EX_NOREDIRECTIONBITMAP = 0x00200000  # 窗口不走重定向位图，PrintWindow 无效

_DPI_SET = False


def _looks_like_gpu_class(classname: str) -> bool:
    """按窗口类名判断是否属于 GPU/合成渲染窗口（PrintWindow 不可靠）。"""
    name = (classname or "").strip()
    if not name:
        return False
    return any(name.startswith(p) for p in _GPU_WINDOW_CLASS_PREFIXES)


def _gpu_window_ext_style(hwnd: int) -> bool:
    """用 WS_EX_NOREDIRECTIONBITMAP 扩展样式识别 GPU 合成窗口。"""
    try:
        return bool(win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & _WS_EX_NOREDIRECTIONBITMAP)
    except Exception:
        return False


def _set_dpi_aware() -> None:
    """让进程 DPI 感知，使窗口坐标为物理像素（否则高 DPI 下截图尺寸偏差）。"""
    global _DPI_SET
    if _DPI_SET:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    _DPI_SET = True


@dataclass(frozen=True)
class Window:
    """描述一个可见顶层窗口。"""

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


def _safe_get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    except Exception:
        return None
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def list_windows() -> list[Window]:
    """枚举所有可见顶层窗口，按左上角排序。"""
    _set_dpi_aware()
    result: list[Window] = []
    handles: list[int] = []

    def _enum(hwnd: int, _: int) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        rect = _safe_get_window_rect(hwnd)
        if rect is None:
            return
        title = win32gui.GetWindowText(hwnd)
        left, top, right, bottom = rect
        result.append(
            Window(hwnd, title, left, top, right - left, bottom - top)
        )

    win32gui.EnumWindows(_enum, 0)
    result.sort(key=lambda w: (w.top, w.left, w.handle))
    return result


def find_window(title_substr: str) -> Window | None:
    """按标题子串（忽略大小写）查找第一个可见窗口。"""
    needle = title_substr.strip().lower()
    for w in list_windows():
        if needle in w.title.lower():
            return w
    return None


def _grab_rect(left: int, top: int, right: int, bottom: int) -> Image.Image:
    return ImageGrab.grab(bbox=(left, top, right, bottom))


def _safe_get_placement(hwnd: int):
    """安全获取窗口的 WINDOWPLACEMENT（用于截图后还原）；失败返回 None。"""
    try:
        return win32gui.GetWindowPlacement(hwnd)
    except Exception:
        return None


def _restore_placement(hwnd: int, placement) -> None:
    """把窗口恢复为截图前的放置状态（位置/尺寸/showCmd）。"""
    if placement is None:
        return
    try:
        win32gui.SetWindowPlacement(hwnd, placement)
    except Exception:
        pass


def _ensure_foreground(hwnd: int) -> None:
    """把窗口置前并置顶，避免被其他窗口遮挡（读合成桌面区域时必需）。

    Windows 会限制后台进程直接 ``SetForegroundWindow``，因此先用常规方式，失败后
    再用 ``AttachThreadInput`` 临时把自己的输入线程挂到目标线程上置前，最后分离。
    """
    try:
        win32gui.SetForegroundWindow(hwnd)
        win32gui.BringWindowToTop(hwnd)
    except Exception:
        pass

    try:
        if win32gui.GetForegroundWindow() == hwnd:
            return
        cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        pid = ctypes.c_ulong()
        fg_tid = ctypes.windll.user32.GetWindowThreadProcessId(
            win32gui.GetForegroundWindow(), ctypes.byref(pid)
        )
        pid2 = ctypes.c_ulong()
        target_tid = ctypes.windll.user32.GetWindowThreadProcessId(
            hwnd, ctypes.byref(pid2)
        )
        if fg_tid and target_tid and fg_tid != target_tid:
            ctypes.windll.user32.AttachThreadInput(cur_tid, target_tid, True)
            try:
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
            finally:
                ctypes.windll.user32.AttachThreadInput(cur_tid, target_tid, False)
    except Exception:
        pass


def _prepare_window_for_capture(hwnd: int, maximize: bool = False) -> None:
    """确保目标窗口可见且在前台，为抓图做准备。

    - ``maximize`` 为 True：最大化并置前（不把焦点还给原窗口）。
    - 否则若窗口处于最小化，恢复它并置前（最小化窗口的矩形在屏幕外，
      PrintWindow 常返回空白）。
    """
    try:
        if maximize:
            # keep_foreground=False：最大化后不把焦点还给原窗口，保持目标窗口可抓
            maximize_window(hwnd, keep_foreground=False)
            _ensure_foreground(hwnd)
        elif win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            _ensure_foreground(hwnd)
    except Exception:
        pass
    # 等待窗口完成最大化/重排/合成，避免抓到手抖的过渡帧
    time.sleep(0.15)


def _is_blank_image(img: Image.Image, max_std: float = 2.0, dominant_ratio: float = 0.98) -> bool:
    """判断画面是否几乎为纯色/空白（含"少数像素有内容"的部分空白帧）。

    背景：``PrintWindow`` 对 GPU 合成窗口（Chromium/Electron 等）常"成功"返回：
    - 一张纯白/纯黑空帧（标准差极小）；
    - 或只渲染出边框/标题栏，主体仍是空的"部分空白帧"（方差被小区域拉高，仅靠
      方差判不出来）。

    因此用两条判定：
    1. 灰度方差足够小（接近纯色）；
    2. 或绝大多数像素落在某个窄亮度带内（主色覆盖占比 ≥ dominant_ratio，
       即内容像素极少）。

    命中任一即视为空白，从而触发读合成桌面区域的回退。
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


def _is_gpu_composited_window(hwnd: int) -> bool:
    """判断窗口是否大概率走 GPU/合成渲染（PrintWindow 不可靠）。

    综合窗口类名与 ``WS_EX_NOREDIRECTIONBITMAP`` 扩展样式判断。命中返回 True 时，
    ``capture_window`` 会直接走读合成桌面区域，跳过 PrintWindow。
    """
    try:
        cls = win32gui.GetClassName(hwnd)
    except Exception:
        cls = ""
    return _looks_like_gpu_class(cls) or _gpu_window_ext_style(hwnd)


def _print_window(hwnd: int) -> Image.Image | None:
    """用 PrintWindow 抓取指定窗口画面（可含被遮挡内容）。失败返回 None。"""
    _set_dpi_aware()
    rect = _safe_get_window_rect(hwnd)
    if rect is None:
        return None
    left, top, right, bottom = rect
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return None

    hwnd_dc = None
    mfc_dc = None
    save_dc = None
    bitmap = None
    try:
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)

        # PW_RENDERFULLCONTENT = 2
        ok = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), _PW_RENDERFULLCONTENT)
        if not ok:
            return None

        info = bitmap.GetInfo()
        bits = bitmap.GetBitmapBits(True)
        img = Image.frombuffer(
            "RGB",
            (info["bmWidth"], info["bmHeight"]),
            bits,
            "raw",
            "BGRX",
            0,
            1,
        )
        return img
    except Exception:
        return None
    finally:
        try:
            if bitmap is not None:
                win32gui.DeleteObject(bitmap.GetHandle())
        except Exception:
            pass
        try:
            if save_dc is not None:
                save_dc.DeleteDC()
        except Exception:
            pass
        try:
            if mfc_dc is not None:
                mfc_dc.DeleteDC()
        except Exception:
            pass
        try:
            if hwnd_dc is not None:
                win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception:
            pass


def maximize_window(handle: int, keep_foreground: bool = True) -> None:
    """最大化指定窗口，默认不切走用户当前的前台焦点。

    参数:
        handle: 窗口句柄（来自 list_windows）。
        keep_foreground: 为 True 时，最大化后把焦点还给原前台窗口，
            避免打断用户当前正在使用的窗口（可能有极短暂的重绘闪烁）。

    异常:
        LookupError: 句柄无效或窗口不可见。
    """
    if not win32gui.IsWindow(handle):
        raise LookupError(f"无效窗口句柄 {handle}")
    _set_dpi_aware()
    prev = win32gui.GetForegroundWindow()
    win32gui.ShowWindow(handle, win32con.SW_MAXIMIZE)
    if keep_foreground and prev and prev != handle:
        # SW_MAXIMIZE 会激活目标窗口，这里把焦点还给原前台窗口，避免切走用户
        try:
            win32gui.SetForegroundWindow(prev)
        except Exception:
            pass
    # 等待最大化动画/重排完成
    time.sleep(0.6)


def capture_window(
    handle: int | None = None,
    title_substr: str | None = None,
    maximize: bool = False,
) -> Image.Image:
    """抓取窗口画面（自愈式：先 PrintWindow，空白则读合成桌面区域）。

    - 传入 ``handle`` 直接抓取该窗口。
    - 传入 ``title_substr`` 按标题子串查找并抓取。
    - ``maximize`` 为 True 时先最大化窗口再抓取，抓取结束后再把窗口恢复为
      最大化前的尺寸/位置/状态（保存原比例，不永久改变窗口布局）。
    - 两者都传时，优先使用 ``handle``。

    抓取策略:
        1. 已知 GPU 合成窗口（Chromium/Electron/UWP 等，按类名或
           ``WS_EX_NOREDIRECTIONBITMAP`` 识别）——直接抓**合成桌面区域**，
           跳过 PrintWindow（对其不可靠，常返回空白/部分帧）。
        2. 否则先 ``PrintWindow``——对普通 GDI 窗口可抓到被遮挡/后台内容。
        3. 若失败（返回 None）**或返回了空白帧**（含部分空白帧），则回退抓取
           **合成桌面区域**：把窗口置前/最大化后 ``ImageGrab`` 窗口矩形
           （DWM 合成桌面能看到 GPU 渲染的真实画面），抓取结束再还原窗口状态。
    """
    _set_dpi_aware()
    if handle is None:
        if not title_substr:
            raise ValueError("capture_window 需要 handle 或 title_substr 之一")
        win = find_window(title_substr)
        if win is None:
            raise LookupError(f"未找到标题含 {title_substr!r} 的窗口")
        handle = win.handle

    # 保存窗口原始状态（showCmd + 位置/尺寸），截图后还原，不永久改变布局
    saved_placement = _safe_get_placement(handle)

    def _grab_region() -> Image.Image:
        """读合成桌面区域：先把窗口置前，避免被其他窗口遮挡。"""
        _ensure_foreground(handle)
        rect = _safe_get_window_rect(handle)
        if rect is None:
            raise RuntimeError(f"窗口 {handle} 无法确定矩形")
        return _grab_rect(*rect)

    try:
        # 预置屏幕状态：最大化（可选）或恢复最小化，保证目标窗口可见且在前台
        _prepare_window_for_capture(handle, maximize=maximize)

        # GPU 合成窗口：跳过 PrintWindow，直接读合成桌面区域
        if _is_gpu_composited_window(handle):
            return _grab_region()

        img = _print_window(handle)
        if img is not None and not _is_blank_image(img):
            return img

        # PrintWindow 抓不到（返回空白/部分空白帧）→ 读合成桌面区域。
        # 若刚最大化过则已是前台；这里再确保一次，避免被遮挡。
        return _grab_region()
    finally:
        _restore_placement(handle, saved_placement)


def capture_screen() -> Image.Image:
    """抓取整屏（多显示器时覆盖全部屏幕）。"""
    _set_dpi_aware()
    return ImageGrab.grab(all_screens=True)

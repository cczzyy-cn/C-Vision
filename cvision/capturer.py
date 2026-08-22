"""Windows 屏幕/窗口捕获：枚举可见顶层窗口、抓取窗口或全屏。

依赖 pywin32 + Pillow（WGC 后端可选依赖 winsdk）。窗口捕获优先级：
    Windows Graphics Capture(真实合成内容) > PrintWindow(PW_RENDERFULLCONTENT) >
    ImageGrab 读合成桌面区域。
WGC 能抓 GPU/Chromium 合成窗口与「被遮挡窗口」的真实内容；PrintWindow 只对普通
GDI 窗口可靠；读合成桌面区域作为最后兜底。
"""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass

import win32con
import win32gui
import win32ui
from PIL import Image, ImageGrab

from cvision.detect import (
    GPU_WINDOW_CLASS_PREFIXES as _GPU_WINDOW_CLASS_PREFIXES,
    is_blank_image as _is_blank_image,
    looks_like_gpu_class as _looks_like_gpu_class,
)

# PrintWindow 的 PW_RENDERFULLCONTENT（Win 8.1+），可捕获前台之外窗口内容
_PW_RENDERFULLCONTENT = 2

_WS_EX_NOREDIRECTIONBITMAP = 0x00200000  # 窗口不走重定向位图，PrintWindow 无效

_DPI_SET = False


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


# ── Windows Graphics Capture (WGC) 后端：抓取窗口「真实合成内容」 ──────────────
# WGC (Win10 1903+) 能捕获 GPU 合成窗口的真实画面，且对「被其它窗口遮挡」的窗口
# 依然有效（比读合成桌面区域更准）。依赖 `winsdk`（WinRT 绑定），未安装或捕获失败
# 时本函数返回 None，由调用方回退到 PrintWindow / 读合成桌面区域。
_WGC_CACHE: bool | None = None


def _wgc_backend_available() -> bool:
    """懒加载判断 winsdk 是否可用（仅探测一次）。"""
    global _WGC_CACHE
    if _WGC_CACHE is None:
        try:
            import winsdk._winrt  # noqa: F401
            _WGC_CACHE = True
        except Exception:
            _WGC_CACHE = False
    return _WGC_CACHE


def capture_window_wgc(hwnd: int, timeout: float = 4.0) -> Image.Image | None:
    """用 Windows Graphics Capture 抓取指定窗口的真实合成内容。

    优点: 针对 GPU/Chromium 合成窗口可靠，能捕获被其它窗口遮挡窗口的内容。
    局限: 无法捕获已最小化（未合成）的窗口内容；依赖 ``winsdk``。

    返回 PIL 图；任何失败/超时/未安装均返回 None（不抛错，由调用方回退）。
    """
    import asyncio
    import threading

    try:
        import winsdk._winrt as wr
        import winsdk.windows.graphics.capture as gc
        from winsdk.windows.graphics.capture.interop import create_for_window
        from winsdk.windows.ai.machinelearning import LearningModelDevice, LearningModelDeviceKind
        from winsdk.windows.graphics.directx import DirectXPixelFormat
        from winsdk.windows.graphics.imaging import SoftwareBitmap, BitmapBufferAccessMode
    except Exception:
        return None

    session = pool = None
    try:
        wr.init_apartment(wr.MTA)
        item = create_for_window(hwnd)
        device = LearningModelDevice(LearningModelDeviceKind.DIRECT_X_HIGH_PERFORMANCE).direct3_d11_device
        pool = gc.Direct3D11CaptureFramePool.create_free_threaded(
            device,
            DirectXPixelFormat.B8_G8_R8_A8_UINT_NORMALIZED,
            1,
            item.size,
        )
        session = pool.create_capture_session(item)
        session.start_capture()

        ev = threading.Event()
        frames = []

        def on_frame(_sender, _args) -> None:
            f = pool.try_get_next_frame()
            if f is not None:
                frames.append(f)
                ev.set()

        pool.add_frame_arrived(on_frame)
        if not ev.wait(timeout):
            return None
        frame = frames[0]

        async def _copy_surface():
            op = SoftwareBitmap.create_copy_from_surface_async(frame.surface)
            return await op

        sb = asyncio.run(_copy_surface())
        buf = sb.lock_buffer(BitmapBufferAccessMode.READ)
        raw = bytes(buf.create_reference())
        # 帧面为 BGRA，这里转成 RGB 的 PIL 图
        return Image.frombytes("RGBA", (sb.pixel_width, sb.pixel_height), raw).convert("RGB")
    except Exception:
        return None
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass
        try:
            if pool is not None:
                pool.close()
        except Exception:
            pass


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
        0. **Windows Graphics Capture (WGC)**：若 ``winsdk`` 可用，优先用它抓窗口的
           **真实合成内容**（对 GPU/Chromium/被遮挡窗口最准）。失败/超时则回退。
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

        # 0. WGC 优先：抓窗口真实合成内容（GPU/被遮挡窗口最准）。失败则回退。
        if _wgc_backend_available():
            wgc_img = capture_window_wgc(handle)
            if wgc_img is not None:
                return wgc_img

        # 1. GPU 合成窗口：跳过 PrintWindow，直接读合成桌面区域
        if _is_gpu_composited_window(handle):
            return _grab_region()

        # 2. 普通 GDI 窗口：优先 PrintWindow（可抓被遮挡内容）
        img = _print_window(handle)
        if img is not None and not _is_blank_image(img):
            return img

        # 3. PrintWindow 抓不到（返回空白/部分空白帧）→ 读合成桌面区域。
        #    若刚最大化过则已是前台；这里再确保一次，避免被遮挡。
        return _grab_region()
    finally:
        _restore_placement(handle, saved_placement)


def capture_screen() -> Image.Image:
    """抓取整屏（多显示器时覆盖全部屏幕）。"""
    _set_dpi_aware()
    return ImageGrab.grab(all_screens=True)

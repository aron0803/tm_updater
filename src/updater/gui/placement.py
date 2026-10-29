"""
Put the window where the user can actually see it.

Spec: docs/specs/gui_folder_dialog_spec.md section 3.1 (placement contract)

Why not ``create_window(x=..., y=...)`` or ``screen=...``: both place the window from
what the toolkit *believes* the screen is, and on a scaled display those units get
mixed.  Measured on the field display (1920x1080 at 124% scaling): pywebview reports
``Screen = 1920x1080, scale = 1.0`` (i.e. device pixels labelled logical) while the
winforms form applies its own ``_scale = 1.24`` - so a 1200 px window becomes 1487
device px placed at x = 360, ending 13 px past the right edge and pushed right of
center.  ``MonitorFromWindow`` + ``GetMonitorInfo`` + ``GetDpiForMonitor`` answer in
device pixels with the monitor's real DPI, which is what centering needs.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
from dataclasses import dataclass

MONITOR_DEFAULTTONEAREST = 2
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
EDGE_MARGIN = 8


@dataclass(frozen=True)
class WorkArea:
    """
    Drawable area of one monitor in device (physical) pixels, plus its DPI scale.

    ``scale`` is needed because the requested window size is in logical pixels:
    1200 logical at 124% is 1487 device px, and centering without converting puts
    the window off the right edge.
    """

    x: int
    y: int
    width: int
    height: int
    scale: float = 1.0


def fit_and_center(
    work: WorkArea, width: int, height: int, margin: int = EDGE_MARGIN
) -> tuple[int, int, int, int]:
    """
    Convert a logical window size to device pixels, clamp it into ``work`` and
    center it - pure math, no I/O.

    Returning the size too matters: a window wider than the monitor (or scaled past
    it) cannot be operated, so it gets clamped instead of hanging off the edge.
    """
    scaled_w = int(round(width * work.scale))
    scaled_h = int(round(height * work.scale))
    max_width = max(1, work.width - margin)
    max_height = max(1, work.height - margin)
    win_w = min(scaled_w, max_width)
    win_h = min(scaled_h, max_height)
    x = work.x + (work.width - win_w) // 2
    y = work.y + (work.height - win_h) // 2
    return x, y, win_w, win_h


def find_window(title: str) -> int:
    """Top-level window handle for an exact title, or 0 when there is none."""
    try:
        return int(ctypes.windll.user32.FindWindowW(None, title))
    except Exception:
        return 0


def _monitor_dpi_scale(monitor: int, hwnd: int) -> float:
    """Effective DPI scale of ``monitor``, falling back to the window, then 1.0."""
    try:
        dpi_x, dpi_y = ctypes.c_uint(), ctypes.c_uint()
        if ctypes.windll.shcore.GetDpiForMonitor(
            monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
        ) == 0 and dpi_x.value:
            return dpi_x.value / 96.0
    except (AttributeError, OSError):
        pass
    try:
        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
        if dpi:
            return dpi / 96.0
    except (AttributeError, OSError):
        pass
    return 1.0


def monitor_work_area(hwnd: int) -> WorkArea | None:
    """
    Work area (taskbar excluded) and DPI scale of the monitor ``hwnd`` sits on.

    Uses the Win32 monitor API: device pixels and the monitor's own DPI, which is
    what pywebview gets wrong on a scaled panel (it reports ``scale = 1.0``).
    """
    if not hwnd:
        return None

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_uint32),
            ("rcMonitor", ctypes.wintypes.RECT),
            ("rcWork", ctypes.wintypes.RECT),
            ("dwFlags", ctypes.c_uint32),
        ]

    try:
        user32 = ctypes.windll.user32
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        rect = info.rcWork
        return WorkArea(
            x=int(rect.left),
            y=int(rect.top),
            width=int(rect.right - rect.left),
            height=int(rect.bottom - rect.top),
            scale=_monitor_dpi_scale(monitor, hwnd),
        )
    except Exception:
        return None


def apply_window_rect(hwnd: int, x: int, y: int, width: int, height: int) -> bool:
    """
    Move and resize in one shot, with device pixels.

    Deliberately not ``Window.move``/``resize``: those take logical pixels and
    multiply by the toolkit's own DPI scale, which is exactly the value that lies
    on a driver-rotated panel.  ``SetWindowPos`` takes what GetMonitorInfo gave us.
    """
    try:
        return bool(
            ctypes.windll.user32.SetWindowPos(
                ctypes.c_void_p(hwnd),
                None,
                int(x),
                int(y),
                int(width),
                int(height),
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
        )
    except Exception:
        return False


def center_on_monitor(title: str, width: int, height: int) -> str:
    """
    Center (and if necessary shrink) the GUI window on the monitor it opened on.

    Returns "" on success, or a message for the GUI log - a badly placed window is
    worth reporting, never worth crashing the updater.
    """
    hwnd = find_window(title)
    if not hwnd:
        return f"找不到視窗「{title}」，無法置中"

    work = monitor_work_area(hwnd)
    if work is None:
        return "讀不到螢幕工作區，無法置中"

    x, y, win_w, win_h = fit_and_center(work, width, height)
    if not apply_window_rect(hwnd, x, y, win_w, win_h):
        return "SetWindowPos 失敗，視窗未置中"

    wanted = (int(round(width * work.scale)), int(round(height * work.scale)))
    if (win_w, win_h) != wanted:
        return (
            f"螢幕工作區 {work.width}x{work.height}（DPI {work.scale:.2f}x）放不下 "
            f"{wanted[0]}x{wanted[1]}，已改為 {win_w}x{win_h} 並置中"
        )
    return ""

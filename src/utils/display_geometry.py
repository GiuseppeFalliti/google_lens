from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import sys

from PySide6.QtGui import QGuiApplication

from src.utils.geometry import Rect


@dataclass(frozen=True, slots=True)
class NativeMonitor:
    name: str
    bounds: Rect


def _normalize_display_name(name: str) -> str:
    return name.replace("\\\\.\\", "").strip().lower()


def _native_monitors() -> list[NativeMonitor]:
    if sys.platform != "win32":
        return []

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
            ("szDevice", wintypes.WCHAR * 32),
        ]

    monitors: list[NativeMonitor] = []
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )

    def callback(hmonitor, hdc, rect_ptr, lparam):
        del hdc, rect_ptr, lparam
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)

        if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            native = info.rcMonitor
            monitors.append(
                NativeMonitor(
                    name=str(info.szDevice),
                    bounds=Rect(
                        int(native.left),
                        int(native.top),
                        int(native.right - native.left),
                        int(native.bottom - native.top),
                    ),
                )
            )
        return True

    callback_fn = callback_type(callback)
    ctypes.windll.user32.EnumDisplayMonitors(
        None,
        None,
        callback_fn,
        0,
    )
    return monitors


def _intersection_area(first: Rect, second: Rect) -> int:
    left = max(first.x, second.x)
    top = max(first.y, second.y)
    right = min(first.right, second.right)
    bottom = min(first.bottom, second.bottom)
    return max(0, right - left) * max(0, bottom - top)


def physical_region_to_qt_logical(region: Rect) -> Rect:
    """Convert a Windows physical-pixel rectangle to Qt logical coordinates.

    MSS/GetCursorPos operate in native Windows desktop pixels while Qt widgets
    use device-independent coordinates. The conversion is done per monitor
    using each monitor's native Windows bounds and its corresponding QScreen
    logical geometry, so it remains correct after monitor/DPI changes.
    """
    region = region.normalized()

    if sys.platform != "win32":
        return region

    native_monitors = _native_monitors()
    qt_screens = QGuiApplication.screens()

    if not native_monitors or not qt_screens:
        return region

    # Prefer the monitor containing the region centre. If the selection crosses
    # monitors, fall back to the monitor with the largest intersection.
    center_x = region.x + region.width // 2
    center_y = region.y + region.height // 2

    native_monitor = next(
        (
            monitor
            for monitor in native_monitors
            if (
                monitor.bounds.x <= center_x < monitor.bounds.right
                and monitor.bounds.y <= center_y < monitor.bounds.bottom
            )
        ),
        None,
    )

    if native_monitor is None:
        native_monitor = max(
            native_monitors,
            key=lambda monitor: _intersection_area(region, monitor.bounds),
        )

    normalized_native_name = _normalize_display_name(native_monitor.name)
    qt_screen = next(
        (
            screen
            for screen in qt_screens
            if _normalize_display_name(screen.name()) == normalized_native_name
        ),
        None,
    )

    # QScreen names normally match Win32 names (DISPLAY1, DISPLAY2, ...).
    # If Windows/Qt expose different naming on a specific system, choose the
    # screen whose physical size estimate is closest to the native monitor.
    if qt_screen is None:
        def size_distance(screen) -> float:
            geometry = screen.geometry()
            dpr = max(0.01, float(screen.devicePixelRatio()))
            physical_width = geometry.width() * dpr
            physical_height = geometry.height() * dpr
            return (
                abs(physical_width - native_monitor.bounds.width)
                + abs(physical_height - native_monitor.bounds.height)
            )

        qt_screen = min(qt_screens, key=size_distance)

    qt_geometry = qt_screen.geometry()
    native_bounds = native_monitor.bounds

    if native_bounds.width <= 0 or native_bounds.height <= 0:
        return region

    scale_x = qt_geometry.width() / native_bounds.width
    scale_y = qt_geometry.height() / native_bounds.height

    logical_x = qt_geometry.x() + round((region.x - native_bounds.x) * scale_x)
    logical_y = qt_geometry.y() + round((region.y - native_bounds.y) * scale_y)
    logical_width = max(1, round(region.width * scale_x))
    logical_height = max(1, round(region.height * scale_y))

    return Rect(
        logical_x,
        logical_y,
        logical_width,
        logical_height,
    )

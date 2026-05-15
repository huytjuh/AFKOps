from __future__ import annotations

import ctypes
import ctypes.wintypes
from dataclasses import dataclass

import cv2
import mss
import numpy as np
import pygetwindow as gw


@dataclass(frozen=True)
class ScreenRegion:
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class CapturedFrame:
    image: np.ndarray
    origin_left: int = 0
    origin_top: int = 0

    def to_screen_position(self, position: tuple[int, int]) -> tuple[int, int]:
        x, y = position
        return self.origin_left + x, self.origin_top + y


class ScreenCapture:
    def grab(self, region: ScreenRegion | None = None) -> np.ndarray:
        return self.grab_frame(region).image

    def grab_frame(self, region: ScreenRegion | None = None) -> CapturedFrame:
        with mss.mss() as screen:
            monitor = (
                {
                    "left": region.left,
                    "top": region.top,
                    "width": region.width,
                    "height": region.height,
                }
                if region
                else screen.monitors[1]
            )
            frame = np.array(screen.grab(monitor))
        image = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return CapturedFrame(
            image=image,
            origin_left=monitor["left"],
            origin_top=monitor["top"],
        )

    def grab_window(self, title: str) -> np.ndarray:
        return self.grab_window_frame(title).image

    def grab_window_frame(self, title: str) -> CapturedFrame:
        return self.grab_frame(self.find_window_region(title))

    def find_window_region(self, title: str, client_area: bool = True) -> ScreenRegion:
        matches = [
            window
            for window in gw.getWindowsWithTitle(title)
            if window.width > 0 and window.height > 0
        ]
        if not matches:
            open_titles = [window.title for window in gw.getAllWindows() if window.title]
            preview = ", ".join(open_titles[:10])
            raise RuntimeError(f"Window not found: {title!r}. Open windows: {preview}")

        window = matches[0]
        if window.isMinimized:
            window.restore()

        client_region = self._find_client_region(window) if client_area else None
        if client_region is not None:
            return client_region

        return ScreenRegion(
            left=window.left,
            top=window.top,
            width=window.width,
            height=window.height,
        )

    def _find_client_region(self, window) -> ScreenRegion | None:
        hwnd = getattr(window, "_hWnd", None)
        if not hwnd:
            return None

        rect = ctypes.wintypes.RECT()
        point = ctypes.wintypes.POINT(0, 0)
        if not ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None
        if not ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point)):
            return None

        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width <= 0 or height <= 0:
            return None

        return ScreenRegion(left=point.x, top=point.y, width=width, height=height)

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Iterable

import psutil
import win32con
import win32gui
import win32process

from lumisync.core.config import WindowConfig

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Rect:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    def clamp_minimum(self, min_width: int, min_height: int) -> "Rect":
        return Rect(
            self.left,
            self.top,
            max(min_width, self.width),
            max(min_height, self.height),
        )


@dataclass(frozen=True, slots=True)
class WindowInfo:
    hwnd: int
    title: str
    class_name: str
    process_name: str
    pid: int
    client_rect: Rect
    minimized: bool


class WindowFinder:
    def __init__(self, config: WindowConfig) -> None:
        self.config = config
        self._cached: WindowInfo | None = None
        self._last_detection = 0.0

    def update_config(self, config: WindowConfig) -> None:
        self.config = config
        self._cached = None
        self._last_detection = 0.0

    def get_window(self) -> WindowInfo | None:
        now = time.monotonic()
        if not self.config.process_name and not self.config.title_contains:
            foreground = self._foreground_candidate()
            if foreground:
                self._cached = foreground
                return foreground

        if self._cached and self._is_handle_usable(self._cached.hwnd):
            if now - self._last_detection < self.config.redetect_interval_seconds:
                refreshed = self._info_from_hwnd(self._cached.hwnd)
                if refreshed:
                    self._cached = refreshed
                    return refreshed

        self._last_detection = now
        candidates = list(self._enumerate_candidates())
        if not candidates:
            if self._cached is not None:
                LOGGER.info("Target window lost; waiting for it to return")
            self._cached = None
            return None

        candidates.sort(key=self._score_window, reverse=True)
        best = candidates[0]
        if self._cached is None or self._cached.hwnd != best.hwnd:
            LOGGER.info(
                "Detected target window hwnd=%s title=%r class=%s pid=%s",
                best.hwnd,
                best.title,
                best.class_name,
                best.pid,
            )
        self._cached = best
        return best

    def list_windows(self) -> list[WindowInfo]:
        return sorted(self._enumerate_candidates(), key=self._score_window, reverse=True)

    def _enumerate_candidates(self) -> Iterable[WindowInfo]:
        handles: list[int] = []

        def callback(hwnd: int, _: object) -> bool:
            handles.append(hwnd)
            return True

        win32gui.EnumWindows(callback, None)
        for hwnd in handles:
            info = self._info_from_hwnd(hwnd)
            if info and self._matches(info):
                yield info

    def _info_from_hwnd(self, hwnd: int) -> WindowInfo | None:
        if not self._is_handle_usable(hwnd):
            return None
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process_name = self._process_name(pid)
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            placement = win32gui.GetWindowPlacement(hwnd)
            minimized = placement[1] == win32con.SW_SHOWMINIMIZED

            left_top = win32gui.ClientToScreen(hwnd, (0, 0))
            right_bottom = win32gui.ClientToScreen(hwnd, win32gui.GetClientRect(hwnd)[2:])
            left, top = left_top
            right, bottom = right_bottom
            rect = Rect(left, top, max(0, right - left), max(0, bottom - top))
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                process_name=process_name,
                pid=pid,
                client_rect=rect,
                minimized=minimized,
            )
        except Exception as exc:
            LOGGER.debug("Failed to inspect window %s: %s", hwnd, exc)
            return None

    def _foreground_candidate(self) -> WindowInfo | None:
        try:
            hwnd = win32gui.GetForegroundWindow()
        except Exception:
            return None
        info = self._info_from_hwnd(hwnd)
        if info and self._matches(info):
            return info
        return None

    def _is_handle_usable(self, hwnd: int) -> bool:
        try:
            return bool(win32gui.IsWindow(hwnd)) and bool(win32gui.IsWindowVisible(hwnd))
        except Exception:
            return False

    def _matches(self, info: WindowInfo) -> bool:
        process_match = (
            not self.config.process_name
            or info.process_name.lower() == self.config.process_name.lower()
        )
        title_match = (
            not self.config.title_contains
            or self.config.title_contains.lower() in info.title.lower()
        )
        large_enough = (
            info.minimized
            or (
                info.client_rect.width >= self.config.min_client_width
                and info.client_rect.height >= self.config.min_client_height
            )
        )
        return process_match and title_match and large_enough

    def _score_window(self, info: WindowInfo) -> tuple[int, int, int]:
        wanted_title = self.config.title_contains.lower()
        title = info.title.lower()
        title_bonus = 10 if wanted_title and wanted_title in title else 0
        minimized_penalty = -20 if info.minimized else 0
        return (title_bonus + minimized_penalty, info.client_rect.area, -info.hwnd)

    @staticmethod
    def _process_name(pid: int) -> str:
        try:
            return psutil.Process(pid).name()
        except psutil.Error:
            return ""


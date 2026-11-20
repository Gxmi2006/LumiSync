from __future__ import annotations

from dataclasses import dataclass
import logging
import sys
import time
from typing import Iterable

import psutil

from lumisync.core.config import WindowConfig
from lumisync.utils.platform_info import IS_LINUX, IS_WINDOWS, linux_session

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


class _Win32Windows:
    """Window access through the Win32 API (pywin32)."""

    def __init__(self) -> None:
        import win32con
        import win32gui
        import win32process

        self._con = win32con
        self._gui = win32gui
        self._process = win32process

    def handles(self) -> list[int]:
        handles: list[int] = []

        def callback(hwnd: int, _: object) -> bool:
            handles.append(hwnd)
            return True

        self._gui.EnumWindows(callback, None)
        return handles

    def foreground(self) -> int | None:
        return self._gui.GetForegroundWindow() or None

    def usable(self, hwnd: int) -> bool:
        return bool(self._gui.IsWindow(hwnd)) and bool(self._gui.IsWindowVisible(hwnd))

    def info(self, hwnd: int) -> WindowInfo:
        gui = self._gui
        _, pid = self._process.GetWindowThreadProcessId(hwnd)
        placement = gui.GetWindowPlacement(hwnd)
        left, top = gui.ClientToScreen(hwnd, (0, 0))
        right, bottom = gui.ClientToScreen(hwnd, gui.GetClientRect(hwnd)[2:])
        return WindowInfo(
            hwnd=hwnd,
            title=gui.GetWindowText(hwnd),
            class_name=gui.GetClassName(hwnd),
            process_name=_process_name(pid),
            pid=pid,
            client_rect=Rect(left, top, max(0, right - left), max(0, bottom - top)),
            minimized=placement[1] == self._con.SW_SHOWMINIMIZED,
        )


class _X11Windows:
    """Window access on Linux X11 through python-xlib, using the EWMH hints
    every modern window manager sets (_NET_ACTIVE_WINDOW, _NET_CLIENT_LIST)."""

    def __init__(self) -> None:
        from Xlib import X, display

        self._X = X
        self._display = display.Display()
        self._root = self._display.screen().root
        atom = self._display.intern_atom
        self._active = atom("_NET_ACTIVE_WINDOW")
        self._client_list = atom("_NET_CLIENT_LIST")
        self._wm_name = atom("_NET_WM_NAME")
        self._utf8 = atom("UTF8_STRING")
        self._wm_pid = atom("_NET_WM_PID")
        self._wm_state = atom("_NET_WM_STATE")
        self._hidden = atom("_NET_WM_STATE_HIDDEN")

    def _property(self, window: object, atom: int, kind: int | None = None):
        try:
            prop = window.get_full_property(atom, kind if kind is not None else self._X.AnyPropertyType)
        except Exception:
            return None
        return None if prop is None else prop.value

    def _window(self, handle: int):
        return self._display.create_resource_object("window", handle)

    def handles(self) -> list[int]:
        value = self._property(self._root, self._client_list)
        return [int(handle) for handle in value] if value is not None else []

    def foreground(self) -> int | None:
        value = self._property(self._root, self._active)
        if value is None or len(value) == 0 or not value[0]:
            return None
        return int(value[0])

    def usable(self, handle: int) -> bool:
        try:
            self._window(handle).get_attributes()
            return True
        except Exception:
            return False

    def info(self, handle: int) -> WindowInfo:
        window = self._window(handle)
        geometry = window.get_geometry()
        # Where the root window's origin sits inside this window, so the
        # window's own position on screen is the negative of it.
        origin = window.translate_coords(self._root, 0, 0)
        title_raw = self._property(window, self._wm_name, self._utf8)
        if isinstance(title_raw, bytes):
            title = title_raw.decode("utf-8", "replace")
        else:
            title = str(title_raw or window.get_wm_name() or "")
        wm_class = window.get_wm_class() or ("", "")
        pid_value = self._property(window, self._wm_pid)
        pid = int(pid_value[0]) if pid_value is not None and len(pid_value) else 0
        state = self._property(window, self._wm_state)
        minimized = state is not None and self._hidden in list(state)
        return WindowInfo(
            hwnd=handle,
            title=title,
            class_name=str(wm_class[-1]),
            process_name=_process_name(pid) if pid else "",
            pid=pid,
            client_rect=Rect(-int(origin.x), -int(origin.y), int(geometry.width), int(geometry.height)),
            minimized=minimized,
        )


def _create_window_backend() -> tuple[object | None, str]:
    """The window API for this system, or None and the reason it is missing."""

    try:
        if IS_WINDOWS:
            return _Win32Windows(), ""
        if IS_LINUX:
            session = linux_session()
            if session == "wayland":
                return None, (
                    "Wayland does not let apps see other windows, so monitor capture is used. "
                    "Log in with an X11 (Xorg) session for active-window sync."
                )
            if session == "none":
                return None, "no graphical session found (DISPLAY is not set)"
            return _X11Windows(), ""
        return None, f"window tracking is not supported on {sys.platform}"
    except Exception as exc:
        return None, f"window tracking unavailable: {exc}"


class WindowFinder:
    def __init__(self, config: WindowConfig) -> None:
        self.config = config
        self._cached: WindowInfo | None = None
        self._last_detection = 0.0
        self._backend, self.unavailable_reason = _create_window_backend()

    @property
    def supported(self) -> bool:
        """False when this system cannot track windows (Wayland, no display)."""

        return self._backend is not None

    def update_config(self, config: WindowConfig) -> None:
        self.config = config
        self._cached = None
        self._last_detection = 0.0

    def get_window(self) -> WindowInfo | None:
        if self._backend is None:
            return None
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
        if self._backend is None:
            return []
        return sorted(self._enumerate_candidates(), key=self._score_window, reverse=True)

    def _enumerate_candidates(self) -> Iterable[WindowInfo]:
        try:
            handles = self._backend.handles()
        except Exception as exc:
            LOGGER.debug("Window enumeration failed: %s", exc)
            return
        for hwnd in handles:
            info = self._info_from_hwnd(hwnd)
            if info and self._matches(info):
                yield info

    def _info_from_hwnd(self, hwnd: int) -> WindowInfo | None:
        if not self._is_handle_usable(hwnd):
            return None
        try:
            return self._backend.info(hwnd)
        except Exception as exc:
            LOGGER.debug("Failed to inspect window %s: %s", hwnd, exc)
            return None

    def _foreground_candidate(self) -> WindowInfo | None:
        try:
            hwnd = self._backend.foreground()
        except Exception:
            return None
        if not hwnd:
            return None
        info = self._info_from_hwnd(hwnd)
        if info and self._matches(info):
            return info
        return None

    def _is_handle_usable(self, hwnd: int) -> bool:
        try:
            return bool(self._backend.usable(hwnd))
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


def _process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name()
    except psutil.Error:
        return ""


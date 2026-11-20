"""Which operating system and desktop session LumiSync is running on."""

from __future__ import annotations

import os
import sys

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")


def linux_session() -> str:
    """``x11``, ``wayland`` or ``none`` (no graphical session, e.g. over SSH).

    Screen capture and window tracking need X11. Under Wayland, apps are not
    allowed to read the screen or see other windows directly.
    """

    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if session_type == "x11" or os.environ.get("DISPLAY"):
        return "x11"
    return "none"


def platform_label() -> str:
    if IS_WINDOWS:
        return "Windows"
    if IS_LINUX:
        return f"Linux ({linux_session()})"
    return sys.platform

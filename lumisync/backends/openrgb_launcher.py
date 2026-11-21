"""Start OpenRGB's SDK server for the user when it is installed but not running.

LumiSync talks to OpenRGB through OpenRGB's SDK server. On PCs where OpenRGB
was installed as a Windows service the server is always running; everywhere
else somebody has to start it. When nothing answers on the configured port,
LumiSync starts OpenRGB itself with ``--server``.

It never starts a second copy of OpenRGB: two copies would fight over the
same RGB hardware. If OpenRGB is already open without its server, the user
is told how to switch the server on instead.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

from lumisync.utils.platform_info import IS_LINUX, IS_WINDOWS

LOGGER = logging.getLogger(__name__)

LOCAL_ADDRESSES = {"127.0.0.1", "localhost", "::1"}
# After LumiSync starts OpenRGB, treat it as "starting" for this long before
# reporting that its server does not answer.
STARTING_GRACE_SECONDS = 90.0

_launched_at: float | None = None
_launched_process: subprocess.Popen | None = None


def is_local_address(address: str) -> bool:
    return address.strip().lower() in LOCAL_ADDRESSES


def server_reachable(address: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((address, port), timeout=timeout):
            return True
    except OSError:
        return False


def find_openrgb(configured_path: str = "") -> list[str] | None:
    """The command that starts OpenRGB, or None when it is not installed."""

    if configured_path:
        path = Path(os.path.expandvars(configured_path)).expanduser()
        return [str(path)] if path.is_file() else None

    if IS_WINDOWS:
        roots = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        ]
        for root in roots:
            candidate = Path(root) / "OpenRGB" / "OpenRGB.exe"
            if root and candidate.is_file():
                return [str(candidate)]
        found = shutil.which("OpenRGB")
        return [found] if found else None

    if IS_LINUX:
        found = shutil.which("openrgb")
        if found:
            return [found]
        if shutil.which("flatpak"):
            try:
                result = subprocess.run(
                    ["flatpak", "info", "org.openrgb.OpenRGB"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
                if result.returncode == 0:
                    return ["flatpak", "run", "org.openrgb.OpenRGB"]
            except Exception:
                pass
    return None


def openrgb_running() -> bool:
    """Whether any OpenRGB process is running for any user."""

    try:
        import psutil
    except Exception:
        return False
    for process in psutil.process_iter(["name"]):
        try:
            name = (process.info.get("name") or "").lower()
        except Exception:
            continue
        if name.startswith("openrgb"):
            return True
    return False


def recently_launched() -> bool:
    return _launched_at is not None and time.monotonic() - _launched_at < STARTING_GRACE_SECONDS


def launched_by_lumisync() -> bool:
    return _launched_at is not None


def launch(command: list[str], port: int) -> None:
    """Start OpenRGB minimized to the tray with its SDK server on ``port``."""

    global _launched_at, _launched_process
    args = [*command, "--server", "--server-port", str(int(port)), "--startminimized"]
    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if IS_WINDOWS:
        # Keep OpenRGB running on its own if LumiSync quits.
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    LOGGER.info("Starting OpenRGB with its SDK server: %s", " ".join(args))
    _launched_process = subprocess.Popen(args, **kwargs)
    _launched_at = time.monotonic()


def _reset_for_tests() -> None:
    global _launched_at, _launched_process
    _launched_at = None
    _launched_process = None

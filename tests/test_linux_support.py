"""Linux code paths, checked on any OS by simulating the platform.

These cannot replace running on a real Linux desktop (screen capture and X11
need a display), but they catch Windows-only imports and broken fallbacks.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from lumisync.capture import window_capture
from lumisync.core import config as config_module
from lumisync.core.config import Config
from lumisync.ui.hotkeys import parse_hotkey
from lumisync.utils import platform_info, startup

REPO_ROOT = Path(__file__).resolve().parents[1]


class ImportWithoutWindowsPackagesTests(unittest.TestCase):
    def test_app_imports_when_windows_packages_are_missing(self) -> None:
        # A fresh process where pywin32, keyboard, pycaw and comtypes do not
        # exist, which is what a Linux install looks like.
        script = textwrap.dedent(
            """
            import sys
            for name in ("win32gui", "win32con", "win32process", "win32api", "win32com",
                         "win32com.client", "pythoncom", "pywintypes", "keyboard",
                         "pycaw", "pycaw.pycaw", "comtypes"):
                sys.modules[name] = None
            import lumisync.core.app
            import lumisync.diagnostics.setup_check
            import lumisync.diagnostics.diagnostics_report
            import lumisync.ui.hotkeys
            import lumisync.utils.startup
            import lumisync.overlays.debug_overlay
            print("imports ok")
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("imports ok", result.stdout)


class LinuxSessionTests(unittest.TestCase):
    def test_session_detection(self) -> None:
        cases = [
            ({"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}, "wayland"),
            ({"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}, "x11"),
            ({"DISPLAY": ":1"}, "x11"),
            ({}, "none"),
        ]
        for env, expected in cases:
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(platform_info.linux_session(), expected, env)

    def test_wayland_has_no_window_tracking_and_explains_why(self) -> None:
        with mock.patch.object(window_capture, "IS_WINDOWS", False), mock.patch.object(
            window_capture, "IS_LINUX", True
        ), mock.patch.object(window_capture, "linux_session", return_value="wayland"):
            finder = window_capture.WindowFinder(Config().window)
        self.assertFalse(finder.supported)
        self.assertIn("X11", finder.unavailable_reason)
        self.assertIsNone(finder.get_window())
        self.assertEqual(finder.list_windows(), [])

    def test_app_falls_back_to_monitor_capture_without_window_tracking(self) -> None:
        from lumisync.core.app import LumiSyncApp

        app = LumiSyncApp.__new__(LumiSyncApp)
        app.config = Config()
        app.window_finder = mock.Mock(supported=False, unavailable_reason="Wayland")
        app._window_fallback_logged = False
        app._capture_monitor_or_region = mock.Mock(return_value="monitor frame")
        self.assertEqual(app._capture_frame(), "monitor frame")
        app._capture_monitor_or_region.assert_called_once_with("monitor")


class LinuxHotkeyParsingTests(unittest.TestCase):
    def test_default_hotkeys_parse(self) -> None:
        defaults = Config().hotkeys
        for combo in (defaults.pause_resume, defaults.reload_config, defaults.quit, defaults.toggle_debug):
            modifiers, key = parse_hotkey(combo)
            self.assertTrue(modifiers)
            self.assertTrue(key)

    def test_names(self) -> None:
        self.assertEqual(parse_hotkey("ctrl+alt+p"), ({"ctrl", "alt"}, "p"))
        self.assertEqual(parse_hotkey("Win+Shift+F9"), ({"super", "shift"}, "F9"))
        self.assertEqual(parse_hotkey("ctrl+page down"), ({"ctrl"}, "Next"))
        with self.assertRaises(ValueError):
            parse_hotkey("hyper+p")
        with self.assertRaises(ValueError):
            parse_hotkey("ctrl+notakey")

    @unittest.skipIf(importlib.util.find_spec("Xlib") is None, "python-xlib not installed")
    def test_xlib_names_used_by_linux_code_exist(self) -> None:
        from Xlib import X, XK, display  # noqa: F401
        from Xlib.error import CatchError  # noqa: F401

        for name in ("LockMask", "Mod2Mask", "ControlMask", "ShiftMask", "Mod1Mask", "Mod4Mask",
                     "GrabModeAsync", "KeyPress", "AnyPropertyType"):
            self.assertTrue(hasattr(X, name), name)
        for key in ("p", "r", "q", "d", "F9", "Next", "Return", "space"):
            self.assertNotEqual(XK.string_to_keysym(key), 0, key)


class LinuxPathsTests(unittest.TestCase):
    def test_config_folder_follows_xdg(self) -> None:
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/home/sam/.config"}, clear=True):
            self.assertEqual(config_module.app_data_dir(), Path("/home/sam/.config") / "LumiSync")
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(Path, "home", return_value=Path("/home/sam")):
            self.assertEqual(config_module.app_data_dir(), Path("/home/sam/.config/LumiSync"))

    def test_autostart_desktop_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}), mock.patch.object(
            startup, "IS_WINDOWS", False
        ), mock.patch.object(startup, "IS_LINUX", True):
            path = startup.install_startup_shortcut(Config(), Path("my config.toml"))
            self.assertEqual(path, Path(tmp) / "autostart" / "lumisync.desktop")
            text = path.read_text(encoding="utf-8")
            self.assertIn("[Desktop Entry]", text)
            self.assertIn("-m lumisync --config", text)
            self.assertIn("'", text)  # the path with a space is quoted
            startup.uninstall_startup_shortcut(Config())
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()

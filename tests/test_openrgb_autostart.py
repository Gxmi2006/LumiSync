from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lumisync.backends import openrgb_launcher
from lumisync.backends.backend_manager import BackendProbeResult, BackendStatusReport, ControllerUnavailable, OpenRgbController
from lumisync.core.config import OpenRgbConfig, RgbConfig
from lumisync.ui.status_messages import describe_backend
from lumisync.ui.tray import TrayIcon

LAUNCHER = "lumisync.backends.backend_manager.openrgb_launcher"


def controller(**overrides) -> OpenRgbController:
    return OpenRgbController(RgbConfig(), OpenRgbConfig(**overrides))


class AutoStartTests(unittest.TestCase):
    def setUp(self) -> None:
        openrgb_launcher._reset_for_tests()

    def tearDown(self) -> None:
        openrgb_launcher._reset_for_tests()

    def test_running_server_is_left_alone(self) -> None:
        with mock.patch(f"{LAUNCHER}.server_reachable", return_value=True), mock.patch(f"{LAUNCHER}.launch") as launch:
            controller()._start_openrgb_if_needed()
        launch.assert_not_called()

    def test_remote_server_is_never_started(self) -> None:
        with mock.patch(f"{LAUNCHER}.server_reachable") as probe, mock.patch(f"{LAUNCHER}.launch") as launch:
            controller(address="192.168.1.20")._start_openrgb_if_needed()
        probe.assert_not_called()
        launch.assert_not_called()

    def test_auto_start_can_be_turned_off(self) -> None:
        with mock.patch(f"{LAUNCHER}.server_reachable") as probe, mock.patch(f"{LAUNCHER}.launch") as launch:
            controller(auto_start=False)._start_openrgb_if_needed()
        probe.assert_not_called()
        launch.assert_not_called()

    def test_open_openrgb_without_server_is_explained_not_duplicated(self) -> None:
        with mock.patch(f"{LAUNCHER}.server_reachable", return_value=False), mock.patch(
            f"{LAUNCHER}.openrgb_running", return_value=True
        ), mock.patch(f"{LAUNCHER}.launch") as launch:
            with self.assertRaises(ControllerUnavailable) as caught:
                controller()._start_openrgb_if_needed()
        self.assertEqual(caught.exception.status, "server off")
        self.assertIn("Start Server", str(caught.exception))
        launch.assert_not_called()

    def test_missing_openrgb_is_explained(self) -> None:
        with mock.patch(f"{LAUNCHER}.server_reachable", return_value=False), mock.patch(
            f"{LAUNCHER}.openrgb_running", return_value=False
        ), mock.patch(f"{LAUNCHER}.find_openrgb", return_value=None):
            with self.assertRaises(ControllerUnavailable) as caught:
                controller()._start_openrgb_if_needed()
        self.assertEqual(caught.exception.status, "not installed")

    def test_installed_openrgb_is_started_with_its_server(self) -> None:
        ctrl = controller(port=6750)
        with mock.patch(f"{LAUNCHER}.server_reachable", return_value=False), mock.patch(
            f"{LAUNCHER}.openrgb_running", return_value=False
        ), mock.patch(f"{LAUNCHER}.find_openrgb", return_value=["C:/OpenRGB/OpenRGB.exe"]), mock.patch(
            "lumisync.backends.openrgb_launcher.subprocess.Popen"
        ) as popen, mock.patch.object(ctrl, "_wait_for_server") as wait:
            ctrl._start_openrgb_if_needed()
        args = popen.call_args.args[0]
        self.assertEqual(args, ["C:/OpenRGB/OpenRGB.exe", "--server", "--server-port", "6750", "--startminimized"])
        wait.assert_called_once_with(timeout=20.0, status_on_timeout="starting")
        self.assertTrue(openrgb_launcher.recently_launched())

    def test_it_is_started_only_once(self) -> None:
        ctrl = controller()
        with mock.patch(f"{LAUNCHER}.server_reachable", return_value=False), mock.patch(
            f"{LAUNCHER}.openrgb_running", return_value=True
        ), mock.patch(f"{LAUNCHER}.recently_launched", return_value=True), mock.patch(
            f"{LAUNCHER}.launch"
        ) as launch, mock.patch.object(ctrl, "_wait_for_server") as wait:
            ctrl._start_openrgb_if_needed()
        launch.assert_not_called()
        wait.assert_called_once_with(status_on_timeout="starting")

    def test_admin_only_openrgb_is_explained(self) -> None:
        error = OSError("The requested operation requires elevation")
        error.winerror = 740
        with mock.patch(f"{LAUNCHER}.server_reachable", return_value=False), mock.patch(
            f"{LAUNCHER}.openrgb_running", return_value=False
        ), mock.patch(f"{LAUNCHER}.find_openrgb", return_value=["OpenRGB.exe"]), mock.patch(
            f"{LAUNCHER}.launch", side_effect=error
        ):
            with self.assertRaises(ControllerUnavailable) as caught:
                controller()._start_openrgb_if_needed()
        self.assertEqual(caught.exception.status, "needs admin")

    def test_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "OpenRGB.exe"
            exe.write_bytes(b"")
            self.assertEqual(openrgb_launcher.find_openrgb(str(exe)), [str(exe)])
        self.assertIsNone(openrgb_launcher.find_openrgb(str(Path(tmp) / "missing.exe")))


def report(status: str, names: tuple[str, ...] = (), active: str = "software fallback") -> BackendStatusReport:
    aura = BackendProbeResult("aura", "Aura", "disabled", "")
    openrgb = BackendProbeResult("openrgb", "OpenRGB", status, "", len(names), names)
    return BackendStatusReport(aura=aura, openrgb=openrgb, active_backend=active)


class StatusMessageTests(unittest.TestCase):
    def test_connected(self) -> None:
        status = describe_backend(report("connected", ("ASUS TUF Laptop Keyboard",), "openrgb"))
        self.assertIn("ASUS TUF Laptop Keyboard", status.tooltip)
        self.assertIsNone(status.notice_message)

    def test_server_off_tells_the_fix(self) -> None:
        status = describe_backend(report("server off"))
        self.assertEqual(status.notice_title, "LumiSync can't reach your lights")
        self.assertIn("SDK Server tab", status.notice_message)

    def test_not_running_tells_the_fix(self) -> None:
        self.assertIn("Start Server", describe_backend(report("not running")).notice_message)

    def test_starting(self) -> None:
        status = describe_backend(report("starting"))
        self.assertEqual(status.notice_title, "Starting OpenRGB")

    def test_output_turned_off_is_quiet(self) -> None:
        self.assertIsNone(describe_backend(report("disabled", active="none")).notice_message)


class TrayNoticeTests(unittest.TestCase):
    def test_notice_waits_until_the_icon_is_ready(self) -> None:
        tray = TrayIcon(lambda: None, lambda: None, lambda: None, lambda: None)
        tray._icon = mock.Mock()
        tray.set_status("LumiSync: lights not connected", "Title", "Message")
        tray._icon.notify.assert_not_called()
        self.assertEqual(tray._icon.title, "LumiSync: lights not connected")
        tray._on_ready(tray._icon)
        tray._icon.notify.assert_called_once_with("Message", "Title")


if __name__ == "__main__":
    unittest.main()

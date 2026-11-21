"""Plain-language status for the tray icon and its pop-up notifications."""

from __future__ import annotations

from dataclasses import dataclass

from lumisync.backends.backend_manager import BackendStatusReport

OPENRGB_FIXES = {
    "not running": "Open OpenRGB, go to the SDK Server tab and click Start Server.",
    "timeout": "Open OpenRGB, go to the SDK Server tab and click Start Server.",
    "server off": "OpenRGB is open, but its server is off. In OpenRGB, go to the SDK Server tab and click Start Server.",
    "not installed": "Install OpenRGB from openrgb.org, then start LumiSync again.",
    "needs admin": "Start OpenRGB yourself, or reinstall it with the Windows service option so it starts with Windows.",
    "no devices": "OpenRGB found no RGB devices. Check the Devices tab in OpenRGB, and close other RGB apps such as Armoury Crate or iCUE.",
    "starting": "LumiSync started OpenRGB for you. Your lights will connect in a few seconds.",
}


@dataclass(frozen=True, slots=True)
class BackendStatus:
    tooltip: str
    notice_title: str | None = None
    notice_message: str | None = None


def describe_backend(report: BackendStatusReport | None) -> BackendStatus:
    if report is None:
        return BackendStatus("LumiSync")
    if report.openrgb.connected:
        names = ", ".join(report.openrgb.device_names[:2]) or "your lights"
        return BackendStatus(f"LumiSync: connected to {names}")
    if report.active_backend == "none" or report.openrgb.status in {"disabled", "skipped"}:
        return BackendStatus("LumiSync: RGB output is off")

    status = report.openrgb.status
    fix = OPENRGB_FIXES.get(status, "Run LumiSync with --setup-check to see what is wrong.")
    if status == "starting":
        return BackendStatus("LumiSync: starting OpenRGB", "Starting OpenRGB", fix)
    return BackendStatus(
        "LumiSync: lights not connected",
        "LumiSync can't reach your lights",
        fix,
    )

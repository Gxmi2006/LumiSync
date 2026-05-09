from __future__ import annotations

import logging

from lumisync.capture.monitor_detection import list_monitors
from lumisync.capture.region_capture import CaptureFrame, ScreenCapturer

LOGGER = logging.getLogger(__name__)


class MonitorCapturer:
    """Capture a full monitor by MSS monitor index."""

    def __init__(self) -> None:
        self._capturer = ScreenCapturer()

    def close(self) -> None:
        self._capturer.close()

    def grab_monitor(self, monitor_index: int = 1) -> CaptureFrame | None:
        monitors = list_monitors()
        matches = [monitor for monitor in monitors if monitor.index == monitor_index]
        if not matches:
            LOGGER.warning("Monitor index %s was not found", monitor_index)
            return None
        return self._capturer.grab(matches[0].rect)

from __future__ import annotations

from dataclasses import dataclass
import logging

import mss

from lumisync.capture.window_capture import Rect

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MonitorInfo:
    index: int
    rect: Rect
    is_virtual_desktop: bool = False

    @property
    def label(self) -> str:
        return "virtual-desktop" if self.is_virtual_desktop else f"monitor-{self.index}"


def list_monitors() -> list[MonitorInfo]:
    """Return monitors visible to MSS.

    MSS index 0 is the virtual desktop rectangle; physical displays start at 1.
    """

    with mss.mss() as capture:
        monitors = []
        for index, monitor in enumerate(capture.monitors):
            monitors.append(
                MonitorInfo(
                    index=index,
                    rect=Rect(
                        int(monitor["left"]),
                        int(monitor["top"]),
                        int(monitor["width"]),
                        int(monitor["height"]),
                    ),
                    is_virtual_desktop=index == 0,
                )
            )
    LOGGER.debug("Detected monitors: %s", monitors)
    return monitors

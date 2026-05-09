from __future__ import annotations

from dataclasses import dataclass
import logging

import mss
import numpy as np

from lumisync.core.config import CaptureConfig
from lumisync.capture.window_capture import Rect, WindowInfo

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CaptureFrame:
    rgb: np.ndarray
    region: Rect


def compute_capture_region(window: WindowInfo, config: CaptureConfig) -> Rect | None:
    client = window.client_rect
    if client.width <= 0 or client.height <= 0:
        return None

    left = client.left + int(client.width * config.left_ratio) + config.left_offset
    top = client.top + int(client.height * config.top_ratio) + config.top_offset
    width = int(client.width * config.width_ratio) + config.width_offset
    height = int(client.height * config.height_ratio) + config.height_offset

    left = max(client.left, min(left, client.right - 1))
    top = max(client.top, min(top, client.bottom - 1))
    right = max(left + 1, min(left + width, client.right))
    bottom = max(top + 1, min(top + height, client.bottom))

    width = right - left
    height = bottom - top
    if width < config.min_width or height < config.min_height:
        LOGGER.debug(
            "Capture region too small: %sx%s, minimum %sx%s",
            width,
            height,
            config.min_width,
            config.min_height,
        )
        return None
    return Rect(left, top, width, height)


class ScreenCapturer:
    def __init__(self) -> None:
        self._mss = mss.mss()

    def close(self) -> None:
        self._mss.close()

    def grab(self, region: Rect) -> CaptureFrame | None:
        monitor = {
            "left": region.left,
            "top": region.top,
            "width": region.width,
            "height": region.height,
        }
        try:
            raw = self._mss.grab(monitor)
        except Exception as exc:
            LOGGER.debug("Screen capture failed for %s: %s", region, exc)
            return None

        bgra = np.asarray(raw, dtype=np.uint8)
        if bgra.ndim != 3 or bgra.shape[2] < 3:
            LOGGER.debug("Unexpected capture frame shape: %s", bgra.shape)
            return None
        rgb = bgra[:, :, :3][:, :, ::-1].copy()
        return CaptureFrame(rgb=rgb, region=region)


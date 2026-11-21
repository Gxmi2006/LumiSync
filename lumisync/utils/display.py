"""Physical screen size helpers.

LumiSync ignores small focal objects by their real size on the screen
(for example "smaller than 0.5 cm"), so it needs to know how many screen
pixels make a centimetre. Displays report their physical size in
millimetres; when that report is missing or nonsense, we assume a standard
96 DPI screen.
"""

from __future__ import annotations

import logging
import os
import sys

LOGGER = logging.getLogger(__name__)

STANDARD_PIXELS_PER_CM = 96 / 2.54  # 37.8
# Anything outside this range is a bogus size report (a projector, a TV, or a
# driver that fills in zeros), so we fall back to the standard value.
MIN_PLAUSIBLE_PIXELS_PER_CM = 15.0
MAX_PLAUSIBLE_PIXELS_PER_CM = 250.0

_cached: float | None = None


def screen_pixels_per_cm(override: float = 0.0) -> float:
    """Pixels per centimetre on the primary display.

    ``override`` (from config) wins when it is above zero. The detected value
    is cached for the life of the process.
    """

    global _cached
    if override and override > 0:
        return float(override)
    if _cached is None:
        detected = None
        try:
            if sys.platform == "win32":
                detected = _windows_pixels_per_cm()
            elif sys.platform.startswith("linux"):
                detected = _x11_pixels_per_cm()
        except Exception as exc:
            LOGGER.debug("Screen size detection failed: %s", exc)
        if detected is None or not (MIN_PLAUSIBLE_PIXELS_PER_CM <= detected <= MAX_PLAUSIBLE_PIXELS_PER_CM):
            if detected is not None:
                LOGGER.info("Ignoring implausible screen density %.1f px/cm", detected)
            detected = STANDARD_PIXELS_PER_CM
        _cached = float(detected)
        LOGGER.info("Screen density: %.1f pixels per cm", _cached)
    return _cached


def _windows_pixels_per_cm() -> float | None:
    import ctypes

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    HORZSIZE, HORZRES = 4, 8  # width in mm, width in pixels
    hdc = user32.GetDC(0)
    if not hdc:
        return None
    try:
        width_mm = gdi32.GetDeviceCaps(hdc, HORZSIZE)
        width_px = gdi32.GetDeviceCaps(hdc, HORZRES)
    finally:
        user32.ReleaseDC(0, hdc)
    if width_mm <= 0 or width_px <= 0:
        return None
    return width_px / (width_mm / 10.0)


def _x11_pixels_per_cm() -> float | None:
    if not os.environ.get("DISPLAY"):
        return None
    from Xlib import display as xdisplay

    disp = xdisplay.Display()
    try:
        screen = disp.screen()
        width_mm = int(screen.width_in_mms)
        width_px = int(screen.width_in_pixels)
    finally:
        disp.close()
    if width_mm <= 0 or width_px <= 0:
        return None
    return width_px / (width_mm / 10.0)

from __future__ import annotations

from collections.abc import Callable
import logging
from threading import Thread

from PIL import Image, ImageDraw

from lumisync.core.color import RGB

LOGGER = logging.getLogger(__name__)


class TrayIcon:
    def __init__(
        self,
        on_pause_resume: Callable[[], None],
        on_reload: Callable[[], None],
        on_toggle_debug: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._on_pause_resume = on_pause_resume
        self._on_reload = on_reload
        self._on_toggle_debug = on_toggle_debug
        self._on_quit = on_quit
        self._icon = None
        self._thread: Thread | None = None
        self._last_color = RGB(0, 128, 255)

    def start(self) -> None:
        try:
            import pystray
        except Exception as exc:
            LOGGER.warning("Tray icon unavailable: %s", exc)
            return

        menu = pystray.Menu(
            pystray.MenuItem("Pause / Resume", lambda _icon, _item: self._on_pause_resume()),
            pystray.MenuItem("Reload Config", lambda _icon, _item: self._on_reload()),
            pystray.MenuItem("Toggle Debug Overlay", lambda _icon, _item: self._on_toggle_debug()),
            pystray.MenuItem("Quit", lambda _icon, _item: self._on_quit()),
        )
        self._icon = pystray.Icon(
            "LumiSync",
            self._make_image(self._last_color),
            "LumiSync",
            menu,
        )
        self._thread = Thread(target=self._run_icon, name="TrayIcon", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                LOGGER.debug("Failed to stop tray icon", exc_info=True)
            self._icon = None

    def update_color(self, color: RGB) -> None:
        self._last_color = color
        if self._icon is not None:
            try:
                self._icon.icon = self._make_image(color)
            except Exception:
                LOGGER.debug("Failed to update tray icon", exc_info=True)

    def _run_icon(self) -> None:
        assert self._icon is not None
        try:
            self._icon.run()
        except Exception as exc:
            LOGGER.warning("Tray icon stopped: %s", exc)

    @staticmethod
    def _make_image(color: RGB) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=10, fill=color.to_tuple() + (255,))
        draw.rectangle((18, 42, 46, 48), fill=(255, 255, 255, 220))
        draw.rectangle((20, 28, 44, 38), fill=(20, 20, 20, 220))
        return image


from __future__ import annotations

from collections.abc import Callable
import logging

from lumisync.core.config import HotkeyConfig

LOGGER = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(
        self,
        config: HotkeyConfig,
        on_pause_resume: Callable[[], None],
        on_reload_config: Callable[[], None],
        on_quit: Callable[[], None],
        on_toggle_debug: Callable[[], None],
    ) -> None:
        self.config = config
        self._callbacks = {
            "pause_resume": on_pause_resume,
            "reload_config": on_reload_config,
            "quit": on_quit,
            "toggle_debug": on_toggle_debug,
        }
        self._keyboard = None
        self._handles: list[object] = []

    def start(self) -> None:
        try:
            import keyboard
        except Exception as exc:
            LOGGER.warning("Global hotkeys unavailable: %s", exc)
            return
        self._keyboard = keyboard
        self._register_all()

    def update_config(self, config: HotkeyConfig) -> None:
        self.config = config
        self.stop(clear_module=False)
        if self._keyboard is not None:
            self._register_all()

    def stop(self, clear_module: bool = True) -> None:
        if self._keyboard is not None:
            for handle in self._handles:
                try:
                    self._keyboard.remove_hotkey(handle)
                except Exception:
                    LOGGER.debug("Failed to remove hotkey", exc_info=True)
        self._handles.clear()
        if clear_module:
            self._keyboard = None

    def _register_all(self) -> None:
        assert self._keyboard is not None
        bindings = {
            self.config.pause_resume: self._callbacks["pause_resume"],
            self.config.reload_config: self._callbacks["reload_config"],
            self.config.quit: self._callbacks["quit"],
            self.config.toggle_debug: self._callbacks["toggle_debug"],
        }
        for combo, callback in bindings.items():
            if not combo:
                continue
            try:
                handle = self._keyboard.add_hotkey(combo, callback)
                self._handles.append(handle)
                LOGGER.info("Registered hotkey %s", combo)
            except Exception as exc:
                LOGGER.warning("Failed to register hotkey %s: %s", combo, exc)


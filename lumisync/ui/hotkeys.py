from __future__ import annotations

from collections.abc import Callable
import logging
from threading import Event, Thread

from lumisync.core.config import HotkeyConfig
from lumisync.utils.platform_info import IS_LINUX, IS_WINDOWS, linux_session

LOGGER = logging.getLogger(__name__)


class HotkeyManager:
    """Global hotkeys.

    Windows uses the ``keyboard`` package. Linux uses X11 key grabs through
    python-xlib, which needs no root access (the ``keyboard`` package does on
    Linux). Wayland does not allow global hotkeys for normal apps, so they are
    skipped there with a log message; the tray menu still works.
    """

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
        self._x11: X11HotkeyListener | None = None
        self._started = False

    def start(self) -> None:
        self._started = True
        if IS_WINDOWS:
            try:
                import keyboard
            except Exception as exc:
                LOGGER.warning("Global hotkeys unavailable: %s", exc)
                return
            self._keyboard = keyboard
        elif IS_LINUX:
            session = linux_session()
            if session != "x11":
                LOGGER.warning(
                    "Global hotkeys need an X11 session (this is %s); use the tray menu instead",
                    session,
                )
                return
        else:
            LOGGER.warning("Global hotkeys are not supported on this system")
            return
        self._register_all()

    def update_config(self, config: HotkeyConfig) -> None:
        self.config = config
        self.stop(clear_module=False)
        if self._started:
            self._register_all()

    def stop(self, clear_module: bool = True) -> None:
        if self._keyboard is not None:
            for handle in self._handles:
                try:
                    self._keyboard.remove_hotkey(handle)
                except Exception:
                    LOGGER.debug("Failed to remove hotkey", exc_info=True)
        self._handles.clear()
        if self._x11 is not None:
            self._x11.stop()
            self._x11 = None
        if clear_module:
            self._keyboard = None
            self._started = False

    def _bindings(self) -> dict[str, Callable[[], None]]:
        bindings = {
            self.config.pause_resume: self._callbacks["pause_resume"],
            self.config.reload_config: self._callbacks["reload_config"],
            self.config.quit: self._callbacks["quit"],
            self.config.toggle_debug: self._callbacks["toggle_debug"],
        }
        return {combo: callback for combo, callback in bindings.items() if combo}

    def _register_all(self) -> None:
        bindings = self._bindings()
        if self._keyboard is not None:
            for combo, callback in bindings.items():
                try:
                    handle = self._keyboard.add_hotkey(combo, callback)
                    self._handles.append(handle)
                    LOGGER.info("Registered hotkey %s", combo)
                except Exception as exc:
                    LOGGER.warning("Failed to register hotkey %s: %s", combo, exc)
        elif IS_LINUX:
            try:
                self._x11 = X11HotkeyListener(bindings)
                self._x11.start()
            except Exception as exc:
                LOGGER.warning("Global hotkeys unavailable: %s", exc)
                self._x11 = None


# X11 names for the key words used in config.toml hotkeys.
_X11_KEY_NAMES = {
    "space": "space",
    "enter": "Return",
    "return": "Return",
    "esc": "Escape",
    "escape": "Escape",
    "tab": "Tab",
    "backspace": "BackSpace",
    "delete": "Delete",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "page up": "Prior",
    "pagedown": "Next",
    "page down": "Next",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "pause": "Pause",
}


def parse_hotkey(combo: str) -> tuple[set[str], str]:
    """Split ``"ctrl+alt+p"`` into its modifiers and the X11 key name.

    Raises ValueError for combos that cannot be bound.
    """

    parts = [part.strip().lower() for part in combo.split("+") if part.strip()]
    if not parts:
        raise ValueError("empty hotkey")
    modifiers: set[str] = set()
    for part in parts[:-1]:
        if part in ("ctrl", "control"):
            modifiers.add("ctrl")
        elif part == "shift":
            modifiers.add("shift")
        elif part in ("alt", "option"):
            modifiers.add("alt")
        elif part in ("win", "windows", "super", "cmd", "meta"):
            modifiers.add("super")
        else:
            raise ValueError(f"unknown modifier {part!r}")
    key = parts[-1]
    if len(key) == 1:
        name = key
    elif key in _X11_KEY_NAMES:
        name = _X11_KEY_NAMES[key]
    elif key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        name = key.upper()
    else:
        raise ValueError(f"unknown key {key!r}")
    return modifiers, name


class X11HotkeyListener:
    """Grabs hotkeys on the X11 root window and runs callbacks on a thread."""

    POLL_SECONDS = 0.05

    def __init__(self, bindings: dict[str, Callable[[], None]]) -> None:
        from Xlib import X, XK, display
        from Xlib.error import CatchError

        self._X = X
        self._display = display.Display()
        self._root = self._display.screen().root
        self._stop = Event()
        self._thread: Thread | None = None
        self._grabs: dict[tuple[int, int], Callable[[], None]] = {}
        # Caps Lock and Num Lock change the modifier state, so each hotkey is
        # grabbed with every combination of them.
        self._ignored = X.LockMask | X.Mod2Mask
        mask_for = {"ctrl": X.ControlMask, "shift": X.ShiftMask, "alt": X.Mod1Mask, "super": X.Mod4Mask}

        for combo, callback in bindings.items():
            try:
                modifiers, key_name = parse_hotkey(combo)
            except ValueError as exc:
                LOGGER.warning("Failed to register hotkey %s: %s", combo, exc)
                continue
            keysym = XK.string_to_keysym(key_name)
            keycode = self._display.keysym_to_keycode(keysym) if keysym else 0
            if not keycode:
                LOGGER.warning("Failed to register hotkey %s: no such key on this keyboard", combo)
                continue
            mask = 0
            for modifier in modifiers:
                mask |= mask_for[modifier]
            catcher = CatchError()
            for extra in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                self._root.grab_key(keycode, mask | extra, True, X.GrabModeAsync, X.GrabModeAsync, onerror=catcher)
            self._display.sync()
            if catcher.get_error():
                LOGGER.warning("Failed to register hotkey %s: another app already uses it", combo)
                continue
            self._grabs[(keycode, mask)] = callback
            LOGGER.info("Registered hotkey %s", combo)

    def start(self) -> None:
        self._thread = Thread(target=self._run, name="X11Hotkeys", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        X = self._X
        while not self._stop.is_set():
            try:
                while self._display.pending_events():
                    event = self._display.next_event()
                    if event.type != X.KeyPress:
                        continue
                    callback = self._grabs.get((event.detail, event.state & ~self._ignored))
                    if callback is not None:
                        try:
                            callback()
                        except Exception:
                            LOGGER.exception("Hotkey action failed")
            except Exception as exc:
                LOGGER.warning("Hotkey listener stopped: %s", exc)
                return
            self._stop.wait(self.POLL_SECONDS)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        try:
            X = self._X
            for keycode, mask in self._grabs:
                for extra in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                    self._root.ungrab_key(keycode, mask | extra)
            self._display.close()
        except Exception:
            LOGGER.debug("Failed to release X11 hotkeys", exc_info=True)

from __future__ import annotations

from dataclasses import dataclass
import argparse
import logging
from pathlib import Path
import signal
from threading import Event, Lock
import time

from lumisync.effects.audio_reactive import AudioPulseProvider
from lumisync.capture.region_capture import ScreenCapturer, compute_capture_region
from lumisync.core.color import BLACK, RGB
from lumisync.processing.palette_extraction import DominantColorExtractor
from lumisync.core.config import Config, load_config
from lumisync.backends.backend_manager import ControllerManager
from lumisync.overlays.debug_overlay import DebugOverlay, OverlayData
from lumisync.ui.hotkeys import HotkeyManager
from lumisync.core.logging_setup import setup_logging
from lumisync.core.smoothing import ColorSmoother
from lumisync.utils.startup import install_startup_shortcut, reconcile_startup, uninstall_startup_shortcut
from lumisync.ui.tray import TrayIcon
from lumisync.capture.window_capture import WindowFinder

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RuntimeState:
    paused: bool = False
    fps: float = 0.0
    last_color: RGB = BLACK
    status: str = "starting"


class LumiSyncApp:
    def __init__(self, config_path: Path | None, debug_overlay_override: bool = False) -> None:
        self.config_path = config_path
        self.config = load_config(config_path)
        if debug_overlay_override:
            self.config.app.debug_overlay = True

        self.state = RuntimeState()
        self._stop = Event()
        self._reload = Event()
        self._lock = Lock()

        self.window_finder = WindowFinder(self.config.window)
        self.capturer = ScreenCapturer()
        self.extractor = DominantColorExtractor(self.config.processing, self.config.gradient)
        self.smoother = ColorSmoother(self.config.smoothing)
        self.controllers = ControllerManager(self.config)
        self.audio = AudioPulseProvider(self.config.audio_pulse)
        self.overlay = DebugOverlay()
        self.hotkeys = HotkeyManager(
            self.config.hotkeys,
            self.toggle_pause,
            self.request_reload,
            self.stop,
            self.toggle_debug_overlay,
        )
        self.tray = TrayIcon(
            self.toggle_pause,
            self.request_reload,
            self.toggle_debug_overlay,
            self.stop,
        )

    def run(self) -> int:
        LOGGER.info("Starting LumiSync")
        if self.config.app.manage_startup_from_config:
            try:
                reconcile_startup(self.config, self.config_path)
            except Exception as exc:
                LOGGER.warning("Startup shortcut reconciliation failed: %s", exc)

        self.hotkeys.start()
        if self.config.app.tray_icon:
            self.tray.start()
        if self.config.app.debug_overlay:
            self.overlay.start()

        report = self.controllers.initialize()
        print(report.to_text(), flush=True)

        self._install_signal_handlers()
        try:
            self._loop()
        finally:
            self._cleanup()
        return 0

    def stop(self) -> None:
        LOGGER.info("Quit requested")
        self._stop.set()

    def toggle_pause(self) -> None:
        with self._lock:
            self.state.paused = not self.state.paused
            self.state.status = "paused" if self.state.paused else "running"
            LOGGER.info("Sync %s", "paused" if self.state.paused else "resumed")

    def request_reload(self) -> None:
        LOGGER.info("Config reload requested")
        self._reload.set()

    def toggle_debug_overlay(self) -> None:
        enabled = self.overlay.toggle()
        self.config.app.debug_overlay = enabled
        LOGGER.info("Debug overlay %s", "enabled" if enabled else "disabled")

    def _loop(self) -> None:
        frame_interval = 1.0 / max(1, min(60, int(self.config.app.fps)))
        last_frame_time = time.monotonic()
        fps_ema = 0.0

        while not self._stop.is_set():
            start = time.monotonic()
            if self._reload.is_set():
                self._reload.clear()
                self._reload_config()
                frame_interval = 1.0 / max(1, min(60, int(self.config.app.fps)))

            if self.state.paused:
                self._set_status("paused")
                time.sleep(0.05)
                continue

            self._process_frame()

            now = time.monotonic()
            dt = max(0.001, now - last_frame_time)
            last_frame_time = now
            instant_fps = 1.0 / dt
            fps_ema = instant_fps if fps_ema == 0.0 else (fps_ema * 0.85 + instant_fps * 0.15)
            self.state.fps = fps_ema

            elapsed = time.monotonic() - start
            sleep_time = max(0.001, frame_interval - elapsed)
            self._stop.wait(sleep_time)

    def _process_frame(self) -> None:
        window = self.window_finder.get_window()
        if window is None:
            self._set_status("waiting for target window")
            return
        if window.minimized:
            self._set_status("target window minimized")
            return

        region = compute_capture_region(window, self.config.capture)
        if region is None:
            self._set_status("capture region invalid")
            return

        frame = self.capturer.grab(region)
        if frame is None:
            self._set_status("capture failed")
            return

        sample = self.extractor.extract(frame.rgb)
        if sample is None:
            self._set_status("no vivid pixels")
            self._update_overlay(region, self.state.last_color)
            return

        target = sample.color.scale_brightness(self.audio.multiplier())
        smoothed = self.smoother.update(target)

        region_colors: tuple[RGB, ...] = ()
        if self.config.gradient.enabled and self.config.gradient.send_regions_to_zones:
            region_colors = tuple(
                color.scale_brightness(self.audio.multiplier())
                for color in sample.region_colors
            )

        updated = self.controllers.set_color(smoothed, region_colors)
        self.state.last_color = smoothed
        self.tray.update_color(smoothed)
        self._set_status("running" if updated else "running")
        self._update_overlay(region, smoothed)

    def _reload_config(self) -> None:
        try:
            new_config = load_config(self.config_path)
        except Exception as exc:
            LOGGER.warning("Config reload failed: %s", exc)
            return

        debug_was_enabled = self.overlay.enabled
        self.config = new_config
        self.window_finder.update_config(new_config.window)
        self.extractor.update_config(new_config.processing, new_config.gradient)
        self.smoother.update_config(new_config.smoothing)
        self.controllers.update_config(new_config)
        self.audio.update_config(new_config.audio_pulse)
        self.hotkeys.update_config(new_config.hotkeys)

        if new_config.app.debug_overlay and not debug_was_enabled:
            self.overlay.start()
        elif not new_config.app.debug_overlay and debug_was_enabled:
            self.overlay.stop()
        LOGGER.info("Config reloaded")

    def _update_overlay(self, region, color: RGB) -> None:
        self.overlay.update(
            OverlayData(
                region=region,
                color=color,
                fps=self.state.fps,
                status=self.state.status,
                controller=self.controllers.name,
            )
        )

    def _set_status(self, status: str) -> None:
        if self.state.status != status:
            LOGGER.info("Status: %s", status)
        self.state.status = status

    def _install_signal_handlers(self) -> None:
        try:
            signal.signal(signal.SIGINT, lambda *_: self.stop())
            signal.signal(signal.SIGTERM, lambda *_: self.stop())
        except Exception:
            LOGGER.debug("Signal handler installation failed", exc_info=True)

    def _cleanup(self) -> None:
        LOGGER.info("Shutting down")
        self.hotkeys.stop()
        self.overlay.stop()
        self.tray.stop()
        self.controllers.close()
        self.capturer.close()


def run_from_args(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve() if args.config else None
    config = load_config(config_path)
    log_path = setup_logging(config.app.log_level)
    LOGGER.info("Logging to %s", log_path)

    if args.install_startup:
        path = install_startup_shortcut(config, config_path)
        print(f"Installed Startup shortcut: {path}")
        return 0
    if args.uninstall_startup:
        path = uninstall_startup_shortcut(config)
        print(f"Removed Startup shortcut if present: {path}")
        return 0
    if args.list_windows:
        finder = WindowFinder(config.window)
        windows = finder.list_windows()
        if not windows:
            print("No matching windows found.")
        for item in windows:
            rect = item.client_rect
            print(
                f"hwnd={item.hwnd} pid={item.pid} minimized={item.minimized} "
                f"rect={rect.left},{rect.top},{rect.width}x{rect.height} "
                f"class={item.class_name!r} title={item.title!r}"
            )
        return 0
    if args.test_color:
        color = RGB.from_hex(args.test_color)
        manager = ControllerManager(config)
        report = manager.initialize()
        print(report.to_text(), flush=True)
        manager.set_color(color)
        print(f"Set test color {color.to_hex()} using {manager.name}")
        manager.close()
        return 0

    app = LumiSyncApp(config_path, debug_overlay_override=args.debug_overlay)
    return app.run()


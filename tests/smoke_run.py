"""End-to-end smoke test on a real desktop session (Windows, or Linux X11 / Xvfb).

Used by the GitHub Actions check. It grabs the real screen, runs the color
engine on it, registers a hotkey, then starts the app for a few seconds
and makes sure it keeps running without errors. Exit code 0 means success.

    python tests/smoke_run.py            # Windows
    xvfb-run -a python tests/smoke_run.py  # Linux without a monitor
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'OK' if ok else 'FAIL'}] {name}{': ' + detail if detail else ''}", flush=True)
    if not ok:
        raise SystemExit(1)


def main() -> None:
    from lumisync.capture.monitor_detection import list_monitors
    from lumisync.capture.region_capture import ScreenCapturer
    from lumisync.capture.window_capture import WindowFinder
    from lumisync.core.config import Config
    from lumisync.processing.palette_extraction import PaletteExtractor
    from lumisync.ui.hotkeys import HotkeyManager
    from lumisync.utils.display import screen_pixels_per_cm
    from lumisync.utils.platform_info import IS_LINUX, platform_label

    print(f"System: {platform_label()}")
    config = Config()

    monitors = list_monitors()
    check("monitor detection", bool(monitors), ", ".join(m.label for m in monitors))
    monitor = next((m for m in monitors if not m.is_virtual_desktop), monitors[0])

    capturer = ScreenCapturer()
    frame = capturer.grab(monitor.rect, (160, 90))
    check("screen capture", frame is not None and frame.rgb.shape == (90, 160, 3))

    density = screen_pixels_per_cm()
    check("screen size detection", density > 0, f"{density:.1f} px/cm")

    extractor = PaletteExtractor(config.processing, config.gradient, config.visual_priority, config.palette)
    extractor.set_screen_scale(monitor.rect.width, density)
    extractor.extract(frame.rgb)  # an empty virtual screen may give no color; it must not crash
    check("color engine", True)

    finder = WindowFinder(config.window)
    check("window tracking", finder.supported, finder.unavailable_reason or "available")
    finder.list_windows()

    hotkeys = HotkeyManager(config.hotkeys, lambda: None, lambda: None, lambda: None, lambda: None)
    hotkeys.start()
    if IS_LINUX:
        check("X11 hotkeys", hotkeys._x11 is not None and bool(hotkeys._x11._grabs))
    hotkeys.stop()
    capturer.close()

    # Start the real app (OpenRGB is absent, so it runs in software fallback).
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.toml"
        text = (REPO_ROOT / "config.toml").read_text(encoding="utf-8")
        config_path.write_text(text.replace('controller = "openrgb"', 'controller = "none"', 1), encoding="utf-8")
        process = subprocess.Popen(
            [sys.executable, "-m", "lumisync", "--config", str(config_path)],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        time.sleep(10)
        still_running = process.poll() is None
        process.terminate()
        try:
            output, _ = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
        print(output[-3000:])
        check("app keeps running for 10 s", still_running)
        check("app reports running", "Status: running" in output)
        check("no errors in app output", "Traceback" not in output)


if __name__ == "__main__":
    main()

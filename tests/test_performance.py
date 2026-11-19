from __future__ import annotations

import time
import unittest
from unittest import mock

import cv2
import numpy as np

from lumisync.capture.region_capture import ScreenCapturer
from lumisync.capture.window_capture import Rect
from lumisync.core.app import LumiSyncApp
from lumisync.core.config import Config, PerformanceConfig, validate_config
from lumisync.processing.palette_engine import _weighted_histogram_color


class FakeShot:
    """Stands in for an mss ScreenShot: a BGRA buffer exposed as an array."""

    def __init__(self, bgra: np.ndarray) -> None:
        self._bgra = bgra

    def __array__(self, dtype=None, copy=None):
        return self._bgra if dtype is None else self._bgra.astype(dtype, copy=False)


class CaptureDownscaleTests(unittest.TestCase):
    def setUp(self) -> None:
        rng = np.random.default_rng(7)
        self.bgra = rng.integers(0, 255, (360, 640, 4), dtype=np.uint8)
        self.capturer = ScreenCapturer.__new__(ScreenCapturer)
        self.capturer._mss = mock.Mock()
        self.capturer._mss.grab.return_value = FakeShot(self.bgra)
        self.region = Rect(0, 0, 640, 360)

    def test_full_resolution_frame_is_rgb(self) -> None:
        frame = self.capturer.grab(self.region)
        self.assertEqual(frame.rgb.shape, (360, 640, 3))
        np.testing.assert_array_equal(frame.rgb[..., 0], self.bgra[..., 2])
        np.testing.assert_array_equal(frame.rgb[..., 2], self.bgra[..., 0])

    def test_downscaled_frame_matches_resizing_the_rgb_frame(self) -> None:
        full = self.capturer.grab(self.region).rgb
        small = self.capturer.grab(self.region, (160, 90)).rgb
        expected = cv2.resize(full, (160, 90), interpolation=cv2.INTER_AREA)
        self.assertEqual(small.shape, (90, 160, 3))
        self.assertLessEqual(int(np.abs(small.astype(int) - expected.astype(int)).max()), 2)


class HistogramColorTests(unittest.TestCase):
    def test_dominant_color_and_palette_order(self) -> None:
        rgb = np.array([[250, 10, 10]] * 30 + [[10, 250, 10]] * 10 + [[10, 10, 250]] * 5, dtype=np.float64)
        weights = np.ones(len(rgb))
        color, confidence, palette = _weighted_histogram_color(rgb, weights, 16)
        self.assertEqual(color.to_tuple(), (250, 10, 10))
        self.assertAlmostEqual(confidence, 30 / 45)
        self.assertEqual([c.to_tuple() for c in palette], [(250, 10, 10), (10, 250, 10), (10, 10, 250)])


class AdaptiveFpsTests(unittest.TestCase):
    def _app(self, **performance) -> LumiSyncApp:
        app = LumiSyncApp.__new__(LumiSyncApp)
        app.config = Config()
        app.config.app.fps = 20
        for key, value in performance.items():
            setattr(app.config.performance, key, value)
        app._last_activity = time.monotonic()
        return app

    def test_active_scene_runs_at_configured_fps(self) -> None:
        self.assertAlmostEqual(self._app()._frame_interval(), 1 / 20)

    def test_static_scene_drops_to_idle_fps(self) -> None:
        app = self._app(idle_fps=5)
        app._last_activity -= LumiSyncApp.IDLE_AFTER_SECONDS + 1
        self.assertAlmostEqual(app._frame_interval(), 1 / 5)

    def test_adaptive_fps_can_be_disabled(self) -> None:
        app = self._app(adaptive_fps=False)
        app._last_activity -= 60
        self.assertAlmostEqual(app._frame_interval(), 1 / 20)

    def test_max_fps_caps_the_loop(self) -> None:
        app = self._app(max_fps=10)
        self.assertAlmostEqual(app._frame_interval(), 1 / 10)

    def test_performance_values_are_validated(self) -> None:
        config = Config()
        config.performance = PerformanceConfig(idle_fps=0, max_fps=500)
        issues = validate_config(config, fix=True)
        self.assertEqual((config.performance.idle_fps, config.performance.max_fps), (1, 60))
        self.assertTrue(any(item.path == "performance.idle_fps" for item in issues))


if __name__ == "__main__":
    unittest.main()

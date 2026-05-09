from __future__ import annotations

import time
import unittest

from lumisync.backends.backend_manager import ControllerManager, _openrgb_status_from_exception
from lumisync.core.color import RGB
from lumisync.core.config import SmoothingConfig
from lumisync.core.smoothing import ColorSmoother


class RuntimeHelperTests(unittest.TestCase):
    def test_backend_selection_is_openrgb_first(self) -> None:
        self.assertTrue(ControllerManager._selection_allows("openrgb", "openrgb"))
        self.assertTrue(ControllerManager._selection_allows("openrgb", "auto"))
        self.assertFalse(ControllerManager._selection_allows("aura", "openrgb"))
        self.assertTrue(ControllerManager._selection_allows("aura", "aura"))

    def test_openrgb_exception_status_mapping(self) -> None:
        self.assertEqual(_openrgb_status_from_exception(ConnectionRefusedError()), "not running")
        self.assertEqual(_openrgb_status_from_exception(TimeoutError()), "timeout")

    def test_smoothing_moves_toward_target(self) -> None:
        smoother = ColorSmoother(SmoothingConfig(strength=0.40, minimum_step=1))
        self.assertEqual(smoother.update(RGB(0, 0, 0)), RGB(0, 0, 0))
        time.sleep(0.01)
        next_color = smoother.update(RGB(255, 100, 20))
        self.assertGreater(next_color.r, 0)
        self.assertLess(next_color.r, 255)
        self.assertGreaterEqual(next_color.g, 1)


if __name__ == "__main__":
    unittest.main()

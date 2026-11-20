from __future__ import annotations

import logging
import unittest

import cv2
import numpy as np

from lumisync.core.color import RGB
from lumisync.core.config import Config, validate_config
from lumisync.processing.palette_extraction import PaletteExtractor
from lumisync.processing.visual_priority import focal_position_allowed

W, H = 1920, 1080
PIXELS_PER_CM = 56.0  # a 16 inch 1920x1200 laptop screen
GREEN = (40, 200, 70)


def ui_frame() -> np.ndarray:
    """A dark app window with some grey text, like a chat or code editor."""

    frame = np.full((H, W, 3), (32, 33, 38), np.uint8)
    for line in range(12):
        cv2.putText(frame, "some chat text here " * 3, (500, 200 + line * 55), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 205), 2)
    return frame


def picked_color(frame: np.ndarray, position_filter: bool = True) -> RGB | None:
    config = Config()
    config.visual_priority.position_filter = position_filter
    extractor = PaletteExtractor(config.processing, config.gradient, config.visual_priority, config.palette)
    extractor.set_screen_scale(frame.shape[1], PIXELS_PER_CM)
    small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
    sample = extractor.extract(small)
    return sample.color if sample else None


def is_greenish(color: RGB | None) -> bool:
    return color is not None and color.g > color.r + 40 and color.g > color.b + 40


class FocalPositionFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logging.disable(logging.INFO)

    @classmethod
    def tearDownClass(cls) -> None:
        logging.disable(logging.NOTSET)

    def test_small_off_center_object_is_ignored(self) -> None:
        frame = ui_frame()
        cv2.circle(frame, (330, 560), 40, GREEN, -1)  # 0.7 cm radius, left side
        self.assertTrue(is_greenish(picked_color(frame, position_filter=False)))
        self.assertFalse(is_greenish(picked_color(frame)))

    def test_small_object_in_center_still_counts(self) -> None:
        frame = ui_frame()
        cv2.circle(frame, (960, 540), 40, GREEN, -1)
        self.assertTrue(is_greenish(picked_color(frame)))

    def test_large_off_center_object_still_counts(self) -> None:
        frame = ui_frame()
        cv2.circle(frame, (330, 560), 110, GREEN, -1)  # 2 cm radius
        self.assertTrue(is_greenish(picked_color(frame)))

    def test_thin_large_ring_counts_at_full_size(self) -> None:
        frame = ui_frame()
        cv2.circle(frame, (330, 560), 100, (60, 230, 255), 6)
        color = picked_color(frame)
        self.assertIsNotNone(color)
        self.assertGreater(color.b, color.r + 40)

    def test_corner_objects_are_always_ignored(self) -> None:
        frame = ui_frame()
        cv2.circle(frame, (1780, 980), 110, GREEN, -1)  # large, bottom right corner
        self.assertFalse(is_greenish(picked_color(frame)))

    def test_row_of_small_icons_is_ignored(self) -> None:
        frame = ui_frame()
        colors = [GREEN, (255, 80, 60), (60, 120, 255), (255, 200, 40), (200, 60, 255), (40, 220, 220)]
        for index, color in enumerate(colors):
            cv2.circle(frame, (700 + index * 90, 1050), 25, color, -1)  # like a taskbar
        color = picked_color(frame)
        self.assertIsNotNone(color)
        self.assertLess(max(color.to_tuple()) - min(color.to_tuple()), 25, f"expected a grey, got {color}")

    def test_small_object_on_colored_scene_gives_scene_color(self) -> None:
        frame = (ui_frame() * 0.4 + np.array([150, 40, 40]) * 0.6).astype(np.uint8)
        cv2.circle(frame, (330, 560), 40, GREEN, -1)
        color = picked_color(frame)
        self.assertIsNotNone(color)
        self.assertGreater(color.r, color.g + 30)

    def test_confetti_scene_still_gives_a_color(self) -> None:
        rng = np.random.default_rng(1)
        frame = np.full((H, W, 3), (15, 15, 20), np.uint8)
        palette = [(255, 60, 90), (255, 170, 40), (60, 200, 255)]
        for _ in range(900):
            center = (int(rng.integers(0, W)), int(rng.integers(0, H)))
            cv2.circle(frame, center, int(rng.integers(6, 14)), palette[int(rng.integers(0, 3))], -1)
        color = picked_color(frame)
        self.assertIsNotNone(color)
        self.assertGreater(max(color.to_tuple()) - min(color.to_tuple()), 60, f"expected a vivid color, got {color}")


class FocalPositionRuleTests(unittest.TestCase):
    def test_rule(self) -> None:
        # 160x90 analysis frame, objects need a 5 px radius unless centred.
        def allowed(x, y, w, h):
            return focal_position_allowed((x, y, w, h), 160, 90, 5.0, 0.5, 0.2)

        self.assertTrue(allowed(76, 41, 8, 8))  # small, centre
        self.assertFalse(allowed(10, 40, 8, 8))  # small, left edge
        self.assertTrue(allowed(5, 30, 20, 20))  # large, left edge
        self.assertFalse(allowed(140, 75, 20, 15))  # large, bottom right corner
        self.assertFalse(allowed(20, 2, 40, 2))  # long thin bar at the top counts as small

    def test_radius_follows_screen_size(self) -> None:
        config = Config()
        extractor = PaletteExtractor(config.processing, config.gradient, config.visual_priority, config.palette)
        extractor.set_screen_scale(1920, 56.0)
        self.assertAlmostEqual(extractor.visual_engine.min_focal_radius_px(160), 56.0 * 160 / 1920)
        extractor.set_screen_scale(960, 56.0)  # a smaller window: each analysis pixel is less screen
        self.assertAlmostEqual(extractor.visual_engine.min_focal_radius_px(160), 56.0 * 160 / 960)

    def test_settings_are_validated(self) -> None:
        config = Config()
        config.visual_priority.min_focal_radius_cm = -3
        config.visual_priority.corner_ratio = 0.9
        validate_config(config, fix=True)
        self.assertEqual(config.visual_priority.min_focal_radius_cm, 0.0)
        self.assertEqual(config.visual_priority.corner_ratio, 0.45)


if __name__ == "__main__":
    unittest.main()

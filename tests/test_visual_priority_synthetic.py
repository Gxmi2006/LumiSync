from __future__ import annotations

import colorsys
import unittest

import cv2
import numpy as np

from lumisync.core.config import Config
from lumisync.processing.palette_extraction import PaletteExtractor


def _hue(rgb: tuple[int, int, int]) -> float:
    return colorsys.rgb_to_hsv(*(channel / 255.0 for channel in rgb))[0]


def _hue_distance(left: float, right: float) -> float:
    distance = abs(left - right) % 1.0
    return min(distance, 1.0 - distance)


def _spotify_like_frame(ring_color: tuple[int, int, int]) -> np.ndarray:
    frame = np.full((1080, 1920, 3), [6, 19, 34], dtype=np.uint8)
    frame[:, :320] = [10, 22, 36]
    frame[:, 1460:] = [8, 18, 30]
    cv2.rectangle(frame, (700, 12), (1280, 68), (24, 42, 70), -1)
    cv2.circle(frame, (960, 560), 350, (28, 70, 44), 48, lineType=cv2.LINE_AA)
    cv2.circle(frame, (960, 560), 355, ring_color, 20, lineType=cv2.LINE_AA)

    rng = np.random.default_rng(4)
    points = rng.integers([0, 0], [1920, 1080], size=(600, 2))
    for x, y in points:
        frame[y, x] = [190, 200, 210]
    return frame


class VisualPrioritySyntheticTests(unittest.TestCase):
    def setUp(self) -> None:
        config = Config()
        self.extractor = PaletteExtractor(
            config.processing,
            config.gradient,
            config.visual_priority,
            config.palette,
        )

    def test_pale_focal_rings_beat_dark_blue_background(self) -> None:
        ring_colors = [
            (80, 150, 90),
            (165, 200, 170),
            (190, 155, 210),
            (210, 180, 140),
            (165, 205, 215),
        ]
        background_hue = _hue((6, 19, 34))

        for ring_color in ring_colors:
            with self.subTest(ring_color=ring_color):
                sample = self.extractor.extract(_spotify_like_frame(ring_color))
                self.assertIsNotNone(sample)

                output = sample.color.to_tuple()
                distance_to_ring = _hue_distance(_hue(output), _hue(ring_color))
                distance_to_background = _hue_distance(_hue(output), background_hue)
                self.assertGreater(max(output), 45)
                self.assertLess(distance_to_ring, 0.14)
                self.assertLess(distance_to_ring, max(0.05, distance_to_background * 0.75))

    def test_neutral_focal_rings_beat_dark_blue_background(self) -> None:
        for ring_color in [(230, 230, 230), (165, 165, 165), (115, 115, 115)]:
            with self.subTest(ring_color=ring_color):
                sample = self.extractor.extract(_spotify_like_frame(ring_color))
                self.assertIsNotNone(sample)

                red, green, blue = sample.color.to_tuple()
                channel_spread = max(red, green, blue) - min(red, green, blue)
                self.assertLess(channel_spread, 32)
                self.assertGreater(max(red, green, blue), 55)

    def test_scene_without_clear_object_still_picks_visible_color(self) -> None:
        frame = np.zeros((540, 960, 3), dtype=np.uint8)
        for x in range(frame.shape[1]):
            blend = x / max(1, frame.shape[1] - 1)
            frame[:, x] = [
                int(48 + blend * 70),
                int(36 + blend * 44),
                int(72 + (1.0 - blend) * 55),
            ]

        sample = self.extractor.extract(frame)
        self.assertIsNotNone(sample)
        hue, saturation, value = colorsys.rgb_to_hsv(
            *(channel / 255.0 for channel in sample.color.to_tuple())
        )
        self.assertGreater(saturation, 0.18)
        self.assertGreater(value, 0.18)
        self.assertGreaterEqual(hue, 0.0)


if __name__ == "__main__":
    unittest.main()

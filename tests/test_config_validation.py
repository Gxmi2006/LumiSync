from __future__ import annotations

import unittest

from lumisync.core.config import Config, validate_config


class ConfigValidationTests(unittest.TestCase):
    def test_invalid_values_are_clamped_when_fixing(self) -> None:
        config = Config()
        config.app.fps = 500
        config.app.controller = "mystery"
        config.capture.left_ratio = -2.0
        config.capture.width_ratio = 5.0
        config.processing.downscale_width = 2
        config.palette.palette_size = 0
        config.openrgb.port = 99999

        issues = validate_config(config, fix=True)

        self.assertGreaterEqual(len(issues), 1)
        self.assertEqual(config.app.fps, 60)
        self.assertEqual(config.app.controller, "openrgb")
        self.assertEqual(config.capture.left_ratio, 0.0)
        self.assertEqual(config.capture.width_ratio, 1.0)
        self.assertEqual(config.processing.downscale_width, 16)
        self.assertEqual(config.palette.palette_size, 1)
        self.assertEqual(config.openrgb.port, 65535)

    def test_valid_defaults_have_no_warnings(self) -> None:
        self.assertEqual(validate_config(Config(), fix=False), [])


if __name__ == "__main__":
    unittest.main()

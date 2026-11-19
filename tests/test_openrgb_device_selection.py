from __future__ import annotations

import unittest
from dataclasses import dataclass, field

from lumisync.backends.backend_manager import OpenRgbController
from lumisync.core.config import OpenRgbConfig, RgbConfig

try:
    from openrgb.utils import DeviceType
except Exception:  # pragma: no cover - openrgb-python is a runtime dependency
    DeviceType = None


@dataclass
class FakeDevice:
    name: str
    type: object
    colors: list = field(default_factory=list)

    def set_color(self, color, fast: bool = False) -> None:
        self.colors.append(color)


@unittest.skipIf(DeviceType is None, "openrgb-python not installed")
class OpenRgbDeviceSelectionTests(unittest.TestCase):
    def _controller(self, **rgb_overrides) -> OpenRgbController:
        rgb = RgbConfig(**rgb_overrides)
        return OpenRgbController(rgb, OpenRgbConfig())

    def test_fan_hub_selected_alongside_keyboard(self) -> None:
        keyboard = FakeDevice("Razer BlackWidow", DeviceType.KEYBOARD)
        hub = FakeDevice("Corsair Commander Core", DeviceType.COOLER)
        selected = self._controller()._select_devices([keyboard, hub])
        self.assertIn(keyboard, selected)
        self.assertIn(hub, selected)

    def test_motherboard_argb_fans_selected_by_type(self) -> None:
        keyboard = FakeDevice("Logitech G213", DeviceType.KEYBOARD)
        board = FakeDevice("MSI MAG B550 TOMAHAWK (MS-7C91)", DeviceType.MOTHERBOARD)
        selected = self._controller()._select_devices([keyboard, board])
        self.assertIn(board, selected)

    def test_fan_named_device_selected_by_name(self) -> None:
        keyboard = FakeDevice("Generic Keyboard", DeviceType.KEYBOARD)
        fans = FakeDevice("Lian Li Uni Fan SL", DeviceType.UNKNOWN)
        selected = self._controller()._select_devices([keyboard, fans])
        self.assertIn(fans, selected)

    def test_keyboard_type_matches_without_name_hint(self) -> None:
        keyboard = FakeDevice("Model XYZ", DeviceType.KEYBOARD)
        headset = FakeDevice("Model ABC", DeviceType.HEADSET)
        selected = self._controller(device_name_contains=[])._select_devices([keyboard, headset])
        self.assertEqual(selected, [keyboard])

    def test_unrelated_devices_still_skipped_when_preferred_exist(self) -> None:
        hub = FakeDevice("Corsair Commander Core", DeviceType.COOLER)
        headset = FakeDevice("SteelSeries Arctis", DeviceType.HEADSET)
        selected = self._controller()._select_devices([hub, headset])
        self.assertEqual(selected, [hub])

    def test_selected_fans_receive_color(self) -> None:
        from openrgb.utils import RGBColor

        from lumisync.core.color import RGB

        controller = self._controller()
        hub = FakeDevice("Corsair Commander Core", DeviceType.COOLER)
        controller._devices = controller._select_devices([hub])
        controller._rgb_color_class = RGBColor
        controller._apply_color(RGB(10, 20, 30), ())
        self.assertEqual(len(hub.colors), 1)
        self.assertEqual((hub.colors[0].red, hub.colors[0].green, hub.colors[0].blue), (10, 20, 30))


if __name__ == "__main__":
    unittest.main()

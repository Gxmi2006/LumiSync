from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Choice:
    key: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class ThemeSelection:
    mood: str = "cinematic"
    multicolor: str = "elegant"
    content: str = "movies"
    intensity: str = "subtle"
    device_preference: str = "keyboard"


MOOD_CHOICES: tuple[Choice, ...] = (
    Choice("cinematic", "Cinematic", "Calm, dimmer, smooth, premium."),
    Choice("balanced", "Balanced", "Natural scene colors with medium responsiveness."),
    Choice("vivid", "Vivid", "Brighter and more colorful for games."),
    Choice("low_power", "Low Power", "Battery-friendly with slower updates."),
)

MULTICOLOR_CHOICES: tuple[Choice, ...] = (
    Choice("elegant", "Elegant multicolor", "Three-color cinematic palette when possible."),
    Choice("single", "Single color", "One best matching scene color."),
    Choice("auto", "Auto", "Use multicolor when OpenRGB exposes zones or LEDs."),
)

CONTENT_CHOICES: tuple[Choice, ...] = (
    Choice("movies", "Movies / anime", "Smoother, darker, cinematic transitions."),
    Choice("games", "Games", "Faster response for interactive scenes."),
    Choice("desktop", "Desktop / browser", "Balanced and gentle for everyday use."),
)

INTENSITY_CHOICES: tuple[Choice, ...] = (
    Choice("subtle", "Subtle", "Lower brightness and saturation."),
    Choice("normal", "Normal", "Medium brightness and color."),
    Choice("bold", "Bold", "Brighter and more saturated."),
)

DEVICE_CHOICES: tuple[Choice, ...] = (
    Choice("keyboard", "Prefer keyboard/laptop devices", "Best for laptop keyboards."),
    Choice("all", "Use all OpenRGB devices", "Best for desktops, strips, RAM, GPU, and mixed setups."),
)


def build_theme_settings(selection: ThemeSelection) -> dict[str, dict[str, Any]]:
    settings = _base_settings()
    _apply_mood(settings, selection.mood)
    _apply_content(settings, selection.content)
    _apply_multicolor(settings, selection.multicolor)
    _apply_intensity(settings, selection.intensity)
    _apply_device_preference(settings, selection.device_preference)
    return settings


def describe_settings(selection: ThemeSelection) -> list[str]:
    settings = build_theme_settings(selection)
    return [
        f"Mood: {_label_for(MOOD_CHOICES, selection.mood)}",
        f"Keyboard colors: {_label_for(MULTICOLOR_CHOICES, selection.multicolor)}",
        f"Main use: {_label_for(CONTENT_CHOICES, selection.content)}",
        f"Intensity: {_label_for(INTENSITY_CHOICES, selection.intensity)}",
        f"OpenRGB devices: {_label_for(DEVICE_CHOICES, selection.device_preference)}",
        f"Palette mode: {settings['palette']['multi_color_mode']}",
        f"FPS: {settings['app']['fps']}",
        f"Smoothing: {settings['smoothing']['strength']}",
    ]


def _base_settings() -> dict[str, dict[str, Any]]:
    return {
        "app": {
            "controller": "openrgb",
            "capture_mode": "active_window",
            "fps": 20,
        },
        "aura": {
            "enabled": False,
        },
        "openrgb": {
            "enabled": True,
            "allow_all_devices_if_no_keyboard": True,
        },
        "palette": {
            "fallback_mode": "scene_harmony",
            "multi_color_mode": "cinematic",
            "minimum_focal_confidence": 0.35,
            "palette_size": 3,
            "harmony_strength": 0.35,
        },
        "gradient": {
            "enabled": True,
            "regions": 3,
            "send_regions_to_zones": True,
        },
        "processing": {
            "downscale_width": 160,
            "downscale_height": 90,
            "brightness_multiplier": 0.78,
            "saturation_multiplier": 1.05,
            "black_threshold": 28,
        },
        "smoothing": {
            "strength": 0.76,
        },
        "rgb": {
            "minimum_update_interval_ms": 16,
            "prefer_keyboard_devices": True,
        },
    }


def _apply_mood(settings: dict[str, dict[str, Any]], mood: str) -> None:
    if mood == "balanced":
        settings["palette"]["multi_color_mode"] = "scene"
        settings["smoothing"]["strength"] = 0.62
        settings["processing"]["brightness_multiplier"] = 0.88
        settings["processing"]["saturation_multiplier"] = 1.12
    elif mood == "vivid":
        settings["palette"]["multi_color_mode"] = "scene"
        settings["smoothing"]["strength"] = 0.48
        settings["processing"]["brightness_multiplier"] = 0.95
        settings["processing"]["saturation_multiplier"] = 1.22
        settings["app"]["fps"] = 24
    elif mood == "low_power":
        settings["palette"]["multi_color_mode"] = "cinematic"
        settings["app"]["fps"] = 10
        settings["processing"]["downscale_width"] = 96
        settings["processing"]["downscale_height"] = 54
        settings["smoothing"]["strength"] = 0.70
        settings["rgb"]["minimum_update_interval_ms"] = 50


def _apply_content(settings: dict[str, dict[str, Any]], content: str) -> None:
    if content == "games":
        settings["app"]["fps"] = max(int(settings["app"]["fps"]), 24)
        settings["smoothing"]["strength"] = min(float(settings["smoothing"]["strength"]), 0.56)
    elif content == "desktop":
        settings["app"]["fps"] = min(int(settings["app"]["fps"]), 18)
        settings["smoothing"]["strength"] = max(float(settings["smoothing"]["strength"]), 0.68)
        settings["processing"]["brightness_multiplier"] = min(
            float(settings["processing"]["brightness_multiplier"]),
            0.82,
        )
    elif content == "movies":
        settings["app"]["fps"] = min(int(settings["app"]["fps"]), 20)
        settings["smoothing"]["strength"] = max(float(settings["smoothing"]["strength"]), 0.76)


def _apply_multicolor(settings: dict[str, dict[str, Any]], multicolor: str) -> None:
    if multicolor == "single":
        settings["gradient"]["enabled"] = False
        settings["gradient"]["send_regions_to_zones"] = False
        settings["palette"]["palette_size"] = 1
    elif multicolor == "auto":
        settings["gradient"]["enabled"] = True
        settings["gradient"]["send_regions_to_zones"] = True
        settings["palette"]["palette_size"] = 2
    else:
        settings["gradient"]["enabled"] = True
        settings["gradient"]["send_regions_to_zones"] = True
        settings["palette"]["palette_size"] = 3


def _apply_intensity(settings: dict[str, dict[str, Any]], intensity: str) -> None:
    if intensity == "normal":
        settings["processing"]["brightness_multiplier"] = min(
            0.92,
            float(settings["processing"]["brightness_multiplier"]) + 0.08,
        )
        settings["processing"]["saturation_multiplier"] = min(
            1.18,
            float(settings["processing"]["saturation_multiplier"]) + 0.07,
        )
    elif intensity == "bold":
        settings["processing"]["brightness_multiplier"] = min(
            1.0,
            float(settings["processing"]["brightness_multiplier"]) + 0.16,
        )
        settings["processing"]["saturation_multiplier"] = min(
            1.28,
            float(settings["processing"]["saturation_multiplier"]) + 0.16,
        )


def _apply_device_preference(settings: dict[str, dict[str, Any]], preference: str) -> None:
    settings["rgb"]["prefer_keyboard_devices"] = preference != "all"
    settings["openrgb"]["allow_all_devices_if_no_keyboard"] = True


def _label_for(choices: tuple[Choice, ...], key: str) -> str:
    for choice in choices:
        if choice.key == key:
            return choice.label
    return key

from __future__ import annotations

from dataclasses import dataclass

from lumisync.core.color import RGB


@dataclass(slots=True)
class AdaptiveBrightness:
    """Normalize brightness while preserving hue enough for ambient lighting."""

    minimum_v: float = 0.10
    maximum_v: float = 0.85
    scene_memory: float = 0.88

    _level: float = 0.5

    def apply(self, color: RGB, scene_luma: float | None = None) -> RGB:
        if scene_luma is not None:
            target = max(0.0, min(1.0, scene_luma))
            self._level = self._level * self.scene_memory + target * (1.0 - self.scene_memory)

        current_peak = max(color.r, color.g, color.b) / 255.0
        if current_peak <= 0.001:
            return color

        desired = max(self.minimum_v, min(self.maximum_v, self._level))
        return color.scale_brightness(desired / current_peak)

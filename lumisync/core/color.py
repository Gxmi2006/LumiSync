from __future__ import annotations

from dataclasses import dataclass
import colorsys
import math
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RGB:
    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "r", self._clamp_channel(self.r))
        object.__setattr__(self, "g", self._clamp_channel(self.g))
        object.__setattr__(self, "b", self._clamp_channel(self.b))

    @staticmethod
    def _clamp_channel(value: float | int) -> int:
        return max(0, min(255, int(round(value))))

    @classmethod
    def from_iterable(cls, values: Iterable[float | int]) -> "RGB":
        r, g, b = values
        return cls(int(round(r)), int(round(g)), int(round(b)))

    @classmethod
    def from_hex(cls, value: str) -> "RGB":
        text = value.strip().removeprefix("#")
        if len(text) != 6:
            raise ValueError(f"Expected RRGGBB hex color, got {value!r}")
        return cls(int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))

    def to_hex(self) -> str:
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def to_tuple(self) -> tuple[int, int, int]:
        return self.r, self.g, self.b

    def distance(self, other: "RGB") -> float:
        return math.sqrt(
            (self.r - other.r) ** 2
            + (self.g - other.g) ** 2
            + (self.b - other.b) ** 2
        )

    def lerp(self, target: "RGB", amount: float) -> "RGB":
        t = max(0.0, min(1.0, amount))
        return RGB(
            self.r + (target.r - self.r) * t,
            self.g + (target.g - self.g) * t,
            self.b + (target.b - self.b) * t,
        )

    def scale_brightness(self, multiplier: float) -> "RGB":
        return RGB(self.r * multiplier, self.g * multiplier, self.b * multiplier)

    def adjust_hsv(
        self,
        saturation_multiplier: float = 1.0,
        brightness_multiplier: float = 1.0,
    ) -> "RGB":
        r, g, b = (channel / 255.0 for channel in self.to_tuple())
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        s = max(0.0, min(1.0, s * saturation_multiplier))
        v = max(0.0, min(1.0, v * brightness_multiplier))
        rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
        return RGB(rr * 255.0, gg * 255.0, bb * 255.0)


BLACK = RGB(0, 0, 0)


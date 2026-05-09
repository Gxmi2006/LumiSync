from __future__ import annotations

import math
import time

from lumisync.core.color import RGB
from lumisync.core.config import SmoothingConfig


class ColorSmoother:
    def __init__(self, config: SmoothingConfig) -> None:
        self.config = config
        self._current: RGB | None = None
        self._last_time: float | None = None

    @property
    def current(self) -> RGB | None:
        return self._current

    def update_config(self, config: SmoothingConfig) -> None:
        self.config = config

    def reset(self) -> None:
        self._current = None
        self._last_time = None

    def update(self, target: RGB) -> RGB:
        now = time.monotonic()
        if self._current is None or self._last_time is None:
            self._current = target
            self._last_time = now
            return target

        dt = max(0.001, now - self._last_time)
        self._last_time = now

        strength = max(0.0, min(0.98, self.config.strength))
        time_constant = 0.025 + strength * 0.70
        amount = 1.0 - math.exp(-dt / time_constant)
        smoothed = self._current.lerp(target, amount)

        if smoothed.distance(self._current) < self.config.minimum_step:
            smoothed = self._nudge_toward(self._current, target)

        self._current = smoothed
        return smoothed

    @staticmethod
    def _nudge_toward(current: RGB, target: RGB) -> RGB:
        def step(c: int, t: int) -> int:
            if c == t:
                return c
            return c + (1 if t > c else -1)

        return RGB(step(current.r, target.r), step(current.g, target.g), step(current.b, target.b))


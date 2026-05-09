from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from lumisync.core.color import RGB

ColorEffect = Callable[[RGB], RGB]


@dataclass(slots=True)
class EffectPipeline:
    """Composable post-processing pipeline for extracted colors."""

    effects: list[ColorEffect] = field(default_factory=list)

    def add(self, effect: ColorEffect) -> None:
        self.effects.append(effect)

    def clear(self) -> None:
        self.effects.clear()

    def apply(self, color: RGB) -> RGB:
        result = color
        for effect in self.effects:
            result = effect(result)
        return result

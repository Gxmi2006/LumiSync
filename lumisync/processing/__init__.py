"""Frame processing and palette extraction pipeline."""

from lumisync.processing.palette_extraction import ColorSample, DominantColorExtractor, PaletteExtractor
from lumisync.processing.visual_priority import (
    VisualPriorityDebug,
    VisualPriorityEngine,
    VisualPriorityResult,
    VisualRegion,
)

__all__ = [
    "ColorSample",
    "DominantColorExtractor",
    "PaletteExtractor",
    "VisualPriorityDebug",
    "VisualPriorityEngine",
    "VisualPriorityResult",
    "VisualRegion",
]

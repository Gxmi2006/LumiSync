from __future__ import annotations

from dataclasses import dataclass
import logging

import cv2
import numpy as np

from lumisync.core.color import RGB
from lumisync.core.config import GradientConfig, ProcessingConfig, VisualPriorityConfig
from lumisync.processing.visual_priority import VisualPriorityDebug, VisualPriorityEngine

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ColorSample:
    color: RGB
    confidence: float
    pixel_count: int
    region_colors: tuple[RGB, ...] = ()
    visual_debug: VisualPriorityDebug | None = None


class PaletteExtractor:
    def __init__(
        self,
        processing: ProcessingConfig,
        gradient: GradientConfig,
        visual_priority: VisualPriorityConfig,
    ) -> None:
        self.processing = processing
        self.gradient = gradient
        self.visual_priority = visual_priority
        self.visual_engine = VisualPriorityEngine(processing, visual_priority)

    def update_config(
        self,
        processing: ProcessingConfig,
        gradient: GradientConfig,
        visual_priority: VisualPriorityConfig,
    ) -> None:
        self.processing = processing
        self.gradient = gradient
        self.visual_priority = visual_priority
        self.visual_engine.update_config(processing, visual_priority)

    def extract(self, rgb_image: np.ndarray) -> ColorSample | None:
        if rgb_image.size == 0:
            return None

        if self.visual_priority.enabled:
            visual = self.visual_engine.extract(rgb_image)
            if visual is not None:
                return ColorSample(
                    color=visual.color,
                    confidence=visual.confidence,
                    pixel_count=visual.pixel_count,
                    region_colors=visual.region_colors,
                    visual_debug=visual.debug,
                )
            LOGGER.debug("Visual priority extraction produced no result; falling back")

        if self.gradient.enabled and self.gradient.regions > 1:
            return self._extract_multi_region(rgb_image)

        return self._extract_single(rgb_image)

    def _extract_multi_region(self, rgb_image: np.ndarray) -> ColorSample | None:
        pieces = self._split_regions(rgb_image)
        samples = [self._extract_single(piece) for piece in pieces]
        valid = [sample for sample in samples if sample is not None]
        if not valid:
            return None

        weights = np.array(
            [max(0.001, sample.confidence * sample.pixel_count) for sample in valid],
            dtype=np.float64,
        )
        colors = np.array([sample.color.to_tuple() for sample in valid], dtype=np.float64)
        avg = np.average(colors, axis=0, weights=weights)
        total_pixels = sum(sample.pixel_count for sample in valid)
        confidence = float(np.average([sample.confidence for sample in valid], weights=weights))
        return ColorSample(
            color=RGB.from_iterable(avg),
            confidence=confidence,
            pixel_count=total_pixels,
            region_colors=tuple(sample.color for sample in valid),
        )

    def _split_regions(self, rgb_image: np.ndarray) -> list[np.ndarray]:
        regions = max(2, int(self.gradient.regions))
        mode = self.gradient.mode.lower()
        if mode == "vertical":
            return [piece for piece in np.array_split(rgb_image, regions, axis=0) if piece.size]
        return [piece for piece in np.array_split(rgb_image, regions, axis=1) if piece.size]

    def _extract_single(self, rgb_image: np.ndarray) -> ColorSample | None:
        cfg = self.processing
        small = self._resize(rgb_image, cfg.downscale_width, cfg.downscale_height)
        hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)

        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        mask = (
            (value >= cfg.black_threshold)
            & (saturation >= cfg.saturation_threshold)
        )

        pixel_count = int(mask.sum())
        if pixel_count < cfg.minimum_mask_pixels:
            LOGGER.debug(
                "Dominant color mask too small: %s pixels below minimum %s",
                pixel_count,
                cfg.minimum_mask_pixels,
            )
            return None

        pixels = small[mask].astype(np.uint16)
        sat = saturation[mask].astype(np.float64) / 255.0
        val = value[mask].astype(np.float64) / 255.0
        weights = np.maximum(0.001, (sat ** 1.5) * (val ** 1.2))

        bins = max(4, min(32, int(cfg.quantization_bins)))
        divisor = max(1, 256 // bins)
        quantized = np.minimum(bins - 1, pixels // divisor)
        keys = (
            quantized[:, 0] * bins * bins
            + quantized[:, 1] * bins
            + quantized[:, 2]
        ).astype(np.int32)

        histogram = np.bincount(keys, weights=weights, minlength=bins**3)
        best_key = int(histogram.argmax())
        dominant_mask = keys == best_key
        if not np.any(dominant_mask):
            return None

        dominant_pixels = pixels[dominant_mask].astype(np.float64)
        dominant_weights = weights[dominant_mask]
        average = np.average(dominant_pixels, axis=0, weights=dominant_weights)
        color = RGB.from_iterable(average).adjust_hsv(
            saturation_multiplier=cfg.saturation_multiplier,
            brightness_multiplier=cfg.brightness_multiplier,
        )

        confidence = float(histogram[best_key] / max(0.001, histogram.sum()))
        return ColorSample(color=color, confidence=confidence, pixel_count=pixel_count)

    @staticmethod
    def _resize(rgb_image: np.ndarray, width: int, height: int) -> np.ndarray:
        target_width = max(16, int(width))
        target_height = max(16, int(height))
        h, w = rgb_image.shape[:2]
        if w == target_width and h == target_height:
            return rgb_image
        return cv2.resize(
            rgb_image,
            (target_width, target_height),
            interpolation=cv2.INTER_AREA,
        )


DominantColorExtractor = PaletteExtractor


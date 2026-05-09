from __future__ import annotations

from dataclasses import dataclass
import logging
import math

import cv2
import numpy as np

from lumisync.core.color import RGB
from lumisync.core.config import ProcessingConfig, VisualPriorityConfig
from lumisync.processing.palette_engine import PaletteResult, extract_weighted_palette
from lumisync.processing.saliency import SaliencyDetector

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VisualRegion:
    bbox: tuple[int, int, int, int]
    score: float
    area_ratio: float
    color: RGB
    confidence: float
    pixel_count: int
    saturation: float
    brightness: float
    contrast: float
    glow: float
    edge_density: float
    center_bias: float


@dataclass(frozen=True, slots=True)
class VisualPriorityDebug:
    regions: tuple[VisualRegion, ...]
    selected_bbox: tuple[float, float, float, float] | None
    region_boxes: tuple[tuple[float, float, float, float, float], ...]
    palette: tuple[RGB, ...]
    saliency_grid: tuple[tuple[int, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class VisualPriorityResult:
    color: RGB
    confidence: float
    pixel_count: int
    region_colors: tuple[RGB, ...]
    debug: VisualPriorityDebug | None


class VisualPriorityEngine:
    def __init__(
        self,
        processing: ProcessingConfig,
        visual_priority: VisualPriorityConfig,
    ) -> None:
        self.processing = processing
        self.visual_priority = visual_priority
        self.saliency = SaliencyDetector(visual_priority)
        self._previous_luma: np.ndarray | None = None
        self._previous_box: tuple[float, float, float, float] | None = None
        self._previous_color: RGB | None = None

    def update_config(
        self,
        processing: ProcessingConfig,
        visual_priority: VisualPriorityConfig,
    ) -> None:
        self.processing = processing
        self.visual_priority = visual_priority
        self.saliency.update_config(visual_priority)

    def extract(self, rgb_image: np.ndarray) -> VisualPriorityResult | None:
        if rgb_image.size == 0:
            return None

        small = _resize(rgb_image, self.processing.downscale_width, self.processing.downscale_height)
        hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        saliency_map = self.saliency.compute(small)
        motion_map = self._motion_map(gray)
        regions = self._extract_regions(small, hsv, gray, saliency_map, motion_map)

        if not regions:
            self._previous_luma = gray
            LOGGER.debug("Visual priority found no focal regions")
            return None

        selected = tuple(regions[: max(1, int(self.visual_priority.selected_regions))])
        result = self._combine_regions(small, hsv, saliency_map, selected)
        self._previous_luma = gray
        if result is None:
            return None

        best_box = _normalize_box(selected[0].bbox, small.shape[1], small.shape[0])
        self._previous_box = best_box
        self._previous_color = result.color

        debug = self._make_debug(saliency_map, selected, result.palette, best_box)
        return VisualPriorityResult(
            color=result.color,
            confidence=result.confidence,
            pixel_count=result.pixel_count,
            region_colors=tuple(region.color for region in selected),
            debug=debug,
        )

    def _extract_regions(
        self,
        rgb: np.ndarray,
        hsv: np.ndarray,
        gray: np.ndarray,
        saliency_map: np.ndarray,
        motion_map: np.ndarray,
    ) -> list[VisualRegion]:
        cfg = self.visual_priority
        h, w = saliency_map.shape[:2]
        frame_area = float(w * h)

        threshold = _adaptive_threshold(saliency_map, cfg.saliency_threshold)
        mask = saliency_map >= threshold

        value = hsv[:, :, 2]
        saturation = hsv[:, :, 1]
        color_mask = (
            (value >= self.processing.black_threshold)
            & (saturation >= max(1, self.processing.saturation_threshold // 2))
        )
        neutral_highlight_mask = (
            (value >= max(82, self.processing.black_threshold * 3))
            & (saturation <= max(42, self.processing.saturation_threshold * 2))
            & (saliency_map >= threshold * 0.72)
        )
        vivid_mask = color_mask | neutral_highlight_mask
        mask &= vivid_mask

        kernel = np.ones((3, 3), dtype=np.uint8)
        mask_u8 = (mask.astype(np.uint8) * 255)
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, kernel, iterations=1)
        mask_u8 = cv2.dilate(mask_u8, kernel, iterations=1)

        count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask_u8, 8)
        regions: list[VisualRegion] = []
        min_area = max(4, int(frame_area * max(0.0, cfg.min_region_area_ratio)))
        max_area = max(min_area, int(frame_area * max(0.01, cfg.max_region_area_ratio)))

        for label in range(1, count):
            x, y, width, height, area = stats[label]
            if area < min_area or area > max_area:
                continue
            padded = _pad_box((int(x), int(y), int(width), int(height)), w, h, cfg.region_padding_ratio)
            region_mask = labels[padded[1] : padded[1] + padded[3], padded[0] : padded[0] + padded[2]] == label
            region = self._score_region(
                rgb,
                hsv,
                gray,
                saliency_map,
                motion_map,
                padded,
                region_mask,
            )
            if region is not None:
                regions.append(region)

        regions.sort(key=lambda item: item.score, reverse=True)
        return regions[: max(1, int(cfg.max_regions))]

    def _score_region(
        self,
        rgb: np.ndarray,
        hsv: np.ndarray,
        gray: np.ndarray,
        saliency_map: np.ndarray,
        motion_map: np.ndarray,
        bbox: tuple[int, int, int, int],
        component_mask: np.ndarray,
    ) -> VisualRegion | None:
        x, y, width, height = bbox
        rgb_roi = rgb[y : y + height, x : x + width]
        hsv_roi = hsv[y : y + height, x : x + width]
        gray_roi = gray[y : y + height, x : x + width]
        saliency_roi = saliency_map[y : y + height, x : x + width]
        motion_roi = motion_map[y : y + height, x : x + width]

        if rgb_roi.size == 0:
            return None

        mask = component_mask
        if mask.shape != gray_roi.shape:
            mask = np.ones(gray_roi.shape, dtype=bool)
        if int(mask.sum()) < self.processing.minimum_mask_pixels:
            return None

        flat_rgb = rgb_roi.reshape(-1, 3)
        flat_hsv = hsv_roi.reshape(-1, 3)
        flat_saliency = saliency_roi.reshape(-1)
        flat_mask = mask.reshape(-1)
        palette = extract_weighted_palette(
            flat_rgb[flat_mask],
            flat_hsv[flat_mask],
            flat_saliency[flat_mask],
            self.processing,
            self.visual_priority,
        )
        if palette is None:
            return None

        saturation = float(np.mean(hsv_roi[:, :, 1][mask]) / 255.0)
        brightness = float(np.mean(hsv_roi[:, :, 2][mask]) / 255.0)
        contrast = float(np.std(gray_roi[mask]))
        glow = float(np.mean(cv2.GaussianBlur(saliency_roi, (0, 0), 2.0)[mask]))
        edge_density = _edge_density(gray_roi, mask)
        area_ratio = float(mask.sum()) / float(rgb.shape[0] * rgb.shape[1])
        center_bias = _center_bias(bbox, rgb.shape[1], rgb.shape[0])
        motion = float(np.mean(motion_roi[mask]))
        temporal = self._temporal_bias(bbox, rgb.shape[1], rgb.shape[0], palette.color)
        neutral_highlight = _neutral_highlight_score(saturation, brightness, contrast, glow, edge_density)

        cfg = self.visual_priority
        score = (
            saturation * cfg.saturation_weight
            + brightness * cfg.brightness_weight
            + contrast * cfg.contrast_weight
            + glow * cfg.glow_weight
            + edge_density * cfg.edge_weight
            + math.sqrt(max(0.0, area_ratio)) * cfg.size_weight
            + center_bias * cfg.center_weight
            + motion * cfg.motion_weight
            + temporal * cfg.temporal_weight
            + neutral_highlight * 0.95
        )

        return VisualRegion(
            bbox=bbox,
            score=float(score),
            area_ratio=area_ratio,
            color=palette.color,
            confidence=palette.confidence,
            pixel_count=palette.pixel_count,
            saturation=saturation,
            brightness=brightness,
            contrast=contrast,
            glow=glow,
            edge_density=edge_density,
            center_bias=center_bias,
        )

    def _combine_regions(
        self,
        rgb: np.ndarray,
        hsv: np.ndarray,
        saliency_map: np.ndarray,
        regions: tuple[VisualRegion, ...],
    ) -> PaletteResult | None:
        if not regions:
            return None

        top_score = max(0.001, regions[0].score)
        weights: list[float] = []
        for index, region in enumerate(regions):
            relative_score = max(0.05, region.score / top_score)
            confidence = max(0.10, region.confidence)
            pixel_weight = max(1.0, float(region.pixel_count) ** 0.35)
            rank_boost = 1.65 if index == 0 else 1.0 / (1.0 + index * 0.45)
            visual_strength = (
                region.saturation * 0.24
                + region.brightness * 0.18
                + region.contrast * 0.16
                + region.glow * 0.18
                + region.edge_density * 0.14
                + region.center_bias * 0.10
            )
            weights.append(
                max(
                    0.001,
                    rank_boost
                    * (relative_score ** 1.45)
                    * (0.45 + visual_strength)
                    * confidence
                    * pixel_weight,
                )
            )

        weights_array = np.array(weights, dtype=np.float64)
        colors = np.array([region.color.to_tuple() for region in regions], dtype=np.float64)
        color = RGB.from_iterable(np.average(colors, axis=0, weights=weights_array))
        palette_confidence = float(np.average([region.confidence for region in regions], weights=weights_array))
        score_confidence = float(
            np.average(
                [
                    min(
                        1.0,
                        (
                            region.score / (region.score + 1.15)
                            + region.glow * 0.28
                            + region.edge_density * 0.18
                            + region.center_bias * 0.12
                        ),
                    )
                    for region in regions
                ],
                weights=weights_array,
            )
        )
        confidence = float(min(1.0, palette_confidence * 0.56 + score_confidence * 0.44))
        return PaletteResult(
            color=color,
            confidence=confidence,
            pixel_count=sum(region.pixel_count for region in regions),
            palette=tuple(region.color for region in regions),
        )

    def _motion_map(self, gray: np.ndarray) -> np.ndarray:
        if self._previous_luma is None or self._previous_luma.shape != gray.shape:
            return np.zeros_like(gray, dtype=np.float32)
        diff = np.abs(gray - self._previous_luma)
        return _normalize01(cv2.GaussianBlur(diff, (0, 0), 1.5))

    def _temporal_bias(
        self,
        bbox: tuple[int, int, int, int],
        width: int,
        height: int,
        color: RGB,
    ) -> float:
        if self._previous_box is None:
            return 0.0
        current = _normalize_box(bbox, width, height)
        overlap = _box_iou(current, self._previous_box)
        color_bias = 0.0
        if self._previous_color is not None:
            color_bias = max(0.0, 1.0 - color.distance(self._previous_color) / 441.7)
        return float(overlap * 0.65 + color_bias * 0.35)

    def _make_debug(
        self,
        saliency_map: np.ndarray,
        regions: tuple[VisualRegion, ...],
        palette: tuple[RGB, ...],
        selected_box: tuple[float, float, float, float],
    ) -> VisualPriorityDebug | None:
        cfg = self.visual_priority
        if not (cfg.debug_regions or cfg.debug_saliency_map or cfg.debug_palette):
            return None

        h, w = saliency_map.shape[:2]
        boxes: list[tuple[float, float, float, float, float]] = []
        if cfg.debug_regions:
            boxes = [
                (*_normalize_box(region.bbox, w, h), region.score)
                for region in regions
            ]

        grid: tuple[tuple[int, ...], ...] = ()
        if cfg.debug_saliency_map:
            preview = cv2.resize(saliency_map, (24, 14), interpolation=cv2.INTER_AREA)
            grid = tuple(tuple(int(max(0, min(255, value * 255))) for value in row) for row in preview)

        return VisualPriorityDebug(
            regions=regions,
            selected_bbox=selected_box,
            region_boxes=tuple(boxes),
            palette=palette if cfg.debug_palette else (),
            saliency_grid=grid,
        )


def _resize(rgb_image: np.ndarray, width: int, height: int) -> np.ndarray:
    target_width = max(16, int(width))
    target_height = max(16, int(height))
    h, w = rgb_image.shape[:2]
    if w == target_width and h == target_height:
        return rgb_image
    return cv2.resize(rgb_image, (target_width, target_height), interpolation=cv2.INTER_AREA)


def _adaptive_threshold(saliency_map: np.ndarray, configured: float) -> float:
    percentile = float(np.percentile(saliency_map, 82.0))
    return max(0.02, min(0.95, max(float(configured), percentile * 0.78)))


def _edge_density(gray_roi: np.ndarray, mask: np.ndarray) -> float:
    sobel_x = cv2.Sobel(gray_roi, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray_roi, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(sobel_x, sobel_y)
    if int(mask.sum()) <= 0:
        return 0.0
    return float(np.mean(np.clip(magnitude[mask] * 2.5, 0.0, 1.0)))


def _neutral_highlight_score(
    saturation: float,
    brightness: float,
    contrast: float,
    glow: float,
    edge_density: float,
) -> float:
    if brightness < 0.30 or saturation > 0.36:
        return 0.0
    brightness_score = min(1.0, max(0.0, (brightness - 0.30) / 0.58))
    neutral_score = min(1.0, max(0.0, (0.36 - saturation) / 0.36))
    structure_score = min(1.0, contrast * 2.1 + glow * 0.55 + edge_density * 0.45)
    return brightness_score * neutral_score * structure_score


def _center_bias(bbox: tuple[int, int, int, int], width: int, height: int) -> float:
    x, y, w, h = bbox
    cx = (x + w * 0.5) / max(1, width)
    cy = (y + h * 0.5) / max(1, height)
    distance = math.sqrt((cx - 0.5) ** 2 + (cy - 0.5) ** 2) / math.sqrt(0.5)
    return max(0.0, 1.0 - distance)


def _pad_box(
    bbox: tuple[int, int, int, int],
    frame_width: int,
    frame_height: int,
    padding_ratio: float,
) -> tuple[int, int, int, int]:
    x, y, w, h = bbox
    padding = int(max(w, h) * max(0.0, padding_ratio))
    left = max(0, x - padding)
    top = max(0, y - padding)
    right = min(frame_width, x + w + padding)
    bottom = min(frame_height, y + h + padding)
    return left, top, max(1, right - left), max(1, bottom - top)


def _normalize_box(
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    return (
        x / max(1, width),
        y / max(1, height),
        w / max(1, width),
        h / max(1, height),
    )


def _box_iou(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    intersection = iw * ih
    union = aw * ah + bw * bh - intersection
    if union <= 1e-6:
        return 0.0
    return intersection / union


def _normalize01(values: np.ndarray) -> np.ndarray:
    min_value = float(values.min())
    max_value = float(values.max())
    span = max_value - min_value
    if span <= 1e-6:
        return np.zeros_like(values, dtype=np.float32)
    return ((values - min_value) / span).astype(np.float32)

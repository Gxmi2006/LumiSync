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
from lumisync.utils.display import STANDARD_PIXELS_PER_CM

LOGGER = logging.getLogger(__name__)

# Small colored pieces are treated as the scene itself (confetti, particles)
# rather than UI clutter when there are at least this many of them and they
# hold more than this share of the colored pixels.
SCENE_TEXTURE_MIN_PIECES = 40
SCENE_TEXTURE_COLOR_SHARE = 0.5
# Colored objects for the position rule: chroma (0-255) at least this, grouped
# into this many hue families.
MIN_OBJECT_CHROMA = 40
HUE_FAMILIES = 12


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
        # Debug payloads are only consumed by the overlay, so callers switch
        # this off to skip building them every frame.
        self.collect_debug = True
        # How the analysed frame maps to the real screen, so small objects can
        # be judged by their physical size. The app sets these every frame.
        self.screen_pixels_per_cm = STANDARD_PIXELS_PER_CM
        self.source_width: int | None = None
        self._input_width = 0
        # Pixels of objects the position filter rejected in the last frame, at
        # analysis resolution. The scene-color fallback skips them too.
        self.excluded_mask: np.ndarray | None = None

    def set_screen_scale(self, source_width: int | None, pixels_per_cm: float) -> None:
        """Tell the engine how wide the captured area is on screen, in pixels."""

        self.source_width = int(source_width) if source_width else None
        self.screen_pixels_per_cm = float(pixels_per_cm) if pixels_per_cm > 0 else STANDARD_PIXELS_PER_CM

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

        self._input_width = int(rgb_image.shape[1])
        self.excluded_mask = None
        small = _resize(rgb_image, self.processing.downscale_width, self.processing.downscale_height)
        hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        saliency_map = self.saliency.compute(small)
        motion_map = self._motion_map(gray)
        if self.visual_priority.position_filter:
            self.excluded_mask = self._small_colored_objects(hsv)
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

        areas = stats[:, cv2.CC_STAT_AREA]
        allowed = np.ones(count, dtype=bool)
        if cfg.position_filter and count > 1:
            # The mask was dilated by one pixel on each side above, so take
            # that back off before measuring how big each object really is.
            allowed = _allowed_by_position(
                stats,
                w,
                h,
                self.min_focal_radius_px(w),
                cfg.center_area_ratio,
                cfg.corner_ratio,
                growth=2,
            )
        candidates = [
            label
            for label in range(1, count)
            if min_area <= areas[label] <= max_area and allowed[label]
        ]
        # Scoring a region is the expensive step, and only `max_regions` survive.
        # On cluttered frames (film grain, busy game scenes) rank components by
        # total saliency first and fully score only the strongest few.
        score_limit = max(4, int(cfg.max_regions) * 3)
        if len(candidates) > score_limit:
            saliency_mass = np.bincount(
                labels.ravel(),
                weights=saliency_map.ravel(),
                minlength=count,
            )
            candidates.sort(key=lambda label: saliency_mass[label], reverse=True)
            candidates = candidates[:score_limit]

        for label in candidates:
            x, y, width, height, area = stats[label]
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

    def _small_colored_objects(self, hsv: np.ndarray) -> np.ndarray | None:
        """Mask of colored objects the position rule rejects.

        This looks at every colored object, not only the salient ones, so tiny
        icons (a taskbar, status dots, colored text) are caught even when the
        focal engine never looked at them. Objects are found separately for
        each hue family, so a green dot on a red background is its own object.
        The scene-color fallback skips the rejected pixels.
        """

        cfg = self.visual_priority
        h, w = hsv.shape[:2]
        hue = hsv[:, :, 0]
        value = hsv[:, :, 2]
        # Chroma (how far from grey) rather than HSV saturation, because dark
        # greys report high saturation while looking grey.
        chroma = hsv[:, :, 1].astype(np.uint16) * value.astype(np.uint16) // 255
        colored = (chroma >= MIN_OBJECT_CHROMA) & (value >= self.processing.black_threshold)
        if not colored.any():
            return None

        min_radius = self.min_focal_radius_px(w)
        hue_family = (hue.astype(np.int32) * HUE_FAMILIES) // 180
        rejected_mask = np.zeros((h, w), dtype=bool)
        rejected_pieces = 0
        rejected_area = 0
        total_area = int(colored.sum())
        for family in np.unique(hue_family[colored]):
            family_mask = (colored & (hue_family == family)).astype(np.uint8)
            count, labels, stats, _centroids = cv2.connectedComponentsWithStats(family_mask, 8)
            rejected = ~_allowed_by_position(stats, w, h, min_radius, cfg.center_area_ratio, cfg.corner_ratio)
            rejected[0] = False  # background
            if rejected.any():
                rejected_mask |= rejected[labels]
                rejected_pieces += int(rejected.sum())
                rejected_area += int(stats[rejected, cv2.CC_STAT_AREA].sum())

        if rejected_pieces == 0:
            return None
        # When the color on screen is mostly many small pieces (confetti,
        # particles, foliage), those pieces are the scene, not UI clutter, so
        # the scene color keeps them. They still never become the focal object.
        # A handful of icons or status dots is still excluded.
        many_pieces = rejected_pieces >= SCENE_TEXTURE_MIN_PIECES
        mostly_pieces = rejected_area > total_area * SCENE_TEXTURE_COLOR_SHARE
        if many_pieces and mostly_pieces:
            return None
        kernel = np.ones((3, 3), dtype=np.uint8)
        return cv2.dilate(rejected_mask.astype(np.uint8), kernel, iterations=1).astype(bool)

    def min_focal_radius_px(self, analysis_width: int) -> float:
        """``min_focal_radius_cm`` converted to pixels of the analysed frame."""

        source_width = self.source_width or self._input_width or analysis_width
        scale = analysis_width / max(1, source_width)
        return float(self.visual_priority.min_focal_radius_cm) * self.screen_pixels_per_cm * scale

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
        if not self.collect_debug:
            return None
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


def focal_position_allowed(
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
    min_radius: float,
    center_area_ratio: float,
    corner_ratio: float,
) -> bool:
    """Whether an object may become the focal color, judged by where it is and its size.

    Objects centred in a corner zone never count. Objects whose radius is
    below ``min_radius`` only count inside the center area. The radius is half
    the geometric mean of the box sides: a disc or a ring gets its real radius
    (a thin ring still counts at full size), while a long thin bar or a line
    of text counts as small.
    """

    stats = np.array([[bbox[0], bbox[1], bbox[2], bbox[3], 0]], dtype=np.int32)
    return bool(_allowed_by_position(stats, width, height, min_radius, center_area_ratio, corner_ratio)[0])


def _allowed_by_position(
    stats: np.ndarray,
    width: int,
    height: int,
    min_radius: float,
    center_area_ratio: float,
    corner_ratio: float,
    growth: int = 0,
) -> np.ndarray:
    """``focal_position_allowed`` for every connected component at once.

    ``growth`` is how many pixels a dilation added to each box side in total;
    it is removed before the size is measured.
    """

    x = stats[:, cv2.CC_STAT_LEFT].astype(np.float64)
    y = stats[:, cv2.CC_STAT_TOP].astype(np.float64)
    box_w = stats[:, cv2.CC_STAT_WIDTH].astype(np.float64)
    box_h = stats[:, cv2.CC_STAT_HEIGHT].astype(np.float64)
    cx = (x + box_w * 0.5) / max(1, width)
    cy = (y + box_h * 0.5) / max(1, height)

    allowed = np.ones(len(stats), dtype=bool)
    if corner_ratio > 0:
        in_corner_column = (cx < corner_ratio) | (cx > 1.0 - corner_ratio)
        in_corner_row = (cy < corner_ratio) | (cy > 1.0 - corner_ratio)
        allowed &= ~(in_corner_column & in_corner_row)

    half = center_area_ratio * 0.5
    in_center = (np.abs(cx - 0.5) <= half) & (np.abs(cy - 0.5) <= half)
    real_w = np.maximum(1.0, box_w - growth)
    real_h = np.maximum(1.0, box_h - growth)
    small = np.sqrt(real_w * real_h) * 0.5 < min_radius
    allowed &= ~(small & ~in_center)
    return allowed


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

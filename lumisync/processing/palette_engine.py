from __future__ import annotations

from dataclasses import dataclass
import logging

import cv2
import numpy as np

from lumisync.core.color import RGB
from lumisync.core.config import ProcessingConfig, VisualPriorityConfig

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PaletteResult:
    color: RGB
    confidence: float
    pixel_count: int
    palette: tuple[RGB, ...] = ()


def extract_weighted_palette(
    rgb_pixels: np.ndarray,
    hsv_pixels: np.ndarray,
    saliency_weights: np.ndarray | None,
    processing: ProcessingConfig,
    visual_priority: VisualPriorityConfig,
) -> PaletteResult | None:
    if rgb_pixels.size == 0 or hsv_pixels.size == 0:
        return None

    saturation = hsv_pixels[:, 1].astype(np.float64) / 255.0
    value = hsv_pixels[:, 2].astype(np.float64) / 255.0
    mask = (
        (hsv_pixels[:, 2] >= processing.black_threshold)
        & (hsv_pixels[:, 1] >= processing.saturation_threshold)
    )
    if int(mask.sum()) < processing.minimum_mask_pixels:
        return None

    rgb = rgb_pixels[mask].astype(np.float64)
    sat = saturation[mask]
    val = value[mask]
    saliency = saliency_weights[mask].astype(np.float64) if saliency_weights is not None else None
    if saliency is not None and len(saliency) >= processing.minimum_mask_pixels * 2:
        percentile = max(0.0, min(0.98, float(visual_priority.color_percentile)))
        cutoff = float(np.quantile(saliency, percentile))
        priority_mask = saliency >= cutoff
        if int(priority_mask.sum()) >= processing.minimum_mask_pixels:
            rgb = rgb[priority_mask]
            sat = sat[priority_mask]
            val = val[priority_mask]
            saliency = saliency[priority_mask]

    weights = np.maximum(
        0.001,
        (sat ** max(0.1, visual_priority.saturation_power))
        * (val ** max(0.1, visual_priority.brightness_power)),
    )
    if saliency is not None:
        weights *= np.maximum(0.05, saliency)

    if visual_priority.use_kmeans and len(rgb) >= max(16, visual_priority.kmeans_clusters * 8):
        color, confidence, palette = _weighted_kmeans_color(
            rgb,
            weights,
            max(2, min(6, int(visual_priority.kmeans_clusters))),
        )
    else:
        color, confidence, palette = _weighted_histogram_color(
            rgb,
            weights,
            max(4, min(32, int(processing.quantization_bins))),
        )

    adjusted = color.adjust_hsv(
        saturation_multiplier=processing.saturation_multiplier,
        brightness_multiplier=processing.brightness_multiplier,
    )
    return PaletteResult(
        color=adjusted,
        confidence=confidence,
        pixel_count=int(mask.sum()),
        palette=palette,
    )


def _weighted_histogram_color(
    rgb: np.ndarray,
    weights: np.ndarray,
    bins: int,
) -> tuple[RGB, float, tuple[RGB, ...]]:
    divisor = max(1, 256 // bins)
    quantized = np.minimum(bins - 1, rgb.astype(np.uint16) // divisor)
    keys = (
        quantized[:, 0] * bins * bins
        + quantized[:, 1] * bins
        + quantized[:, 2]
    ).astype(np.int32)

    histogram = np.bincount(keys, weights=weights, minlength=bins**3)
    if histogram.sum() <= 0:
        return RGB.from_iterable(np.average(rgb, axis=0)), 0.0, ()

    top_keys = np.argsort(histogram)[-3:][::-1]
    best_key = int(top_keys[0])
    dominant_mask = keys == best_key
    dominant_rgb = rgb[dominant_mask]
    dominant_weights = weights[dominant_mask]
    color = RGB.from_iterable(np.average(dominant_rgb, axis=0, weights=dominant_weights))
    confidence = float(histogram[best_key] / max(0.001, histogram.sum()))

    palette: list[RGB] = []
    for key in top_keys:
        if histogram[int(key)] <= 0:
            continue
        key_mask = keys == int(key)
        palette.append(RGB.from_iterable(np.average(rgb[key_mask], axis=0, weights=weights[key_mask])))
    return color, confidence, tuple(palette)


def _weighted_kmeans_color(
    rgb: np.ndarray,
    weights: np.ndarray,
    clusters: int,
) -> tuple[RGB, float, tuple[RGB, ...]]:
    sample_limit = 2500
    if len(rgb) > sample_limit:
        # Deterministic stride sampling keeps CPU predictable and avoids RNG cost.
        stride = max(1, len(rgb) // sample_limit)
        rgb = rgb[::stride]
        weights = weights[::stride]

    data = rgb.astype(np.float32)
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        12,
        1.0,
    )
    try:
        _compactness, labels, centers = cv2.kmeans(
            data,
            clusters,
            None,
            criteria,
            2,
            cv2.KMEANS_PP_CENTERS,
        )
    except cv2.error as exc:
        LOGGER.debug("KMeans palette extraction failed; falling back to average: %s", exc)
        return RGB.from_iterable(np.average(rgb, axis=0, weights=weights)), 0.0, ()

    labels = labels.reshape(-1)
    cluster_weights = np.bincount(labels, weights=weights, minlength=clusters)
    best = int(cluster_weights.argmax())
    confidence = float(cluster_weights[best] / max(0.001, cluster_weights.sum()))
    order = np.argsort(cluster_weights)[::-1]
    palette = tuple(RGB.from_iterable(centers[idx]) for idx in order if cluster_weights[idx] > 0)
    return RGB.from_iterable(centers[best]), confidence, palette

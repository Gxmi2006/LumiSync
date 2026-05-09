from __future__ import annotations

from dataclasses import dataclass
import colorsys
import logging

import cv2
import numpy as np

from lumisync.core.color import RGB
from lumisync.core.config import PaletteConfig, ProcessingConfig, VisualPriorityConfig

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


def extract_scene_harmony_palette(
    rgb_image: np.ndarray,
    processing: ProcessingConfig,
    visual_priority: VisualPriorityConfig,
    palette_config: PaletteConfig,
) -> PaletteResult | None:
    """Extract a pleasant scene color when no single focal object wins.

    This is intentionally still lightweight: it downsamples once, masks out
    near-black and low-color pixels, groups candidates by HSV family, then
    ranks clusters by vividness, coverage, contrast, and weighted share.
    """

    if rgb_image.size == 0:
        return None

    small = _resize_image(rgb_image, processing.downscale_width, processing.downscale_height)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0

    sat_u8 = hsv[:, :, 1]
    val_u8 = hsv[:, :, 2]
    saturation = sat_u8.astype(np.float64) / 255.0
    value = val_u8.astype(np.float64) / 255.0

    saturation_floor = max(8, int(processing.saturation_threshold * 0.55))
    value_floor = max(8, int(processing.black_threshold * 0.85))
    mask = (val_u8 >= value_floor) & (sat_u8 >= saturation_floor)

    if int(mask.sum()) < processing.minimum_mask_pixels:
        saturation_floor = max(4, int(processing.saturation_threshold * 0.30))
        value_floor = max(6, int(processing.black_threshold * 0.65))
        mask = (val_u8 >= value_floor) & (sat_u8 >= saturation_floor)

    if int(mask.sum()) < processing.minimum_mask_pixels:
        return None

    rgb = small.reshape(-1, 3).astype(np.float64)
    hsv_flat = hsv.reshape(-1, 3)
    gray_flat = gray.reshape(-1)
    mask_flat = mask.reshape(-1)

    valid_rgb = rgb[mask_flat]
    valid_hsv = hsv_flat[mask_flat]
    valid_gray = gray_flat[mask_flat]
    valid_sat = saturation.reshape(-1)[mask_flat]
    valid_val = value.reshape(-1)[mask_flat]

    hue_bins = 24
    sat_bins = 6
    val_bins = 6
    hue_key = np.minimum(hue_bins - 1, valid_hsv[:, 0].astype(np.int32) * hue_bins // 180)
    sat_key = np.minimum(sat_bins - 1, valid_hsv[:, 1].astype(np.int32) * sat_bins // 256)
    val_key = np.minimum(val_bins - 1, valid_hsv[:, 2].astype(np.int32) * val_bins // 256)
    keys = hue_key * sat_bins * val_bins + sat_key * val_bins + val_key
    key_count = hue_bins * sat_bins * val_bins

    pixel_weights = np.maximum(
        0.001,
        (valid_sat ** max(0.1, visual_priority.saturation_power * 0.82))
        * (valid_val ** max(0.1, visual_priority.brightness_power * 0.85)),
    )
    weighted_hist = np.bincount(keys, weights=pixel_weights, minlength=key_count)
    count_hist = np.bincount(keys, minlength=key_count)
    if weighted_hist.sum() <= 0:
        return None

    candidate_keys = np.argsort(weighted_hist)[-18:][::-1]
    scored: list[tuple[float, int, RGB, float]] = []
    total_weight = float(weighted_hist.sum())
    total_pixels = max(1, len(valid_rgb))

    for key in candidate_keys:
        key = int(key)
        if count_hist[key] <= 0:
            continue
        key_mask = keys == key
        cluster_weight = pixel_weights[key_mask]
        cluster_rgb = valid_rgb[key_mask]
        cluster_sat = valid_sat[key_mask]
        cluster_val = valid_val[key_mask]
        cluster_gray = valid_gray[key_mask]

        weighted_share = float(weighted_hist[key] / max(0.001, total_weight))
        coverage = float(count_hist[key] / total_pixels)
        colorfulness = float(np.mean(cluster_sat) * np.sqrt(max(0.0, np.mean(cluster_val))))
        coverage_score = min(1.0, float(np.sqrt(coverage * 10.0)))
        contrast = float(np.std(cluster_gray) * 2.5)
        elegance = _scene_elegance_score(cluster_sat, cluster_val)

        score = (
            weighted_share * 0.34
            + colorfulness * 0.28
            + coverage_score * 0.20
            + min(1.0, contrast) * 0.10
            + elegance * 0.08
        )
        color = RGB.from_iterable(np.average(cluster_rgb, axis=0, weights=cluster_weight))
        scored.append((score, key, color, weighted_share))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, _best_key, best_color, best_share = scored[0]
    adjusted = best_color.adjust_hsv(
        saturation_multiplier=processing.saturation_multiplier,
        brightness_multiplier=processing.brightness_multiplier,
    )
    scene_palette = _dedupe_palette(
        [
            color.adjust_hsv(
                saturation_multiplier=processing.saturation_multiplier,
                brightness_multiplier=processing.brightness_multiplier,
            )
            for _score, _key, color, _share in scored
        ],
        max(1, int(palette_config.palette_size)),
    )
    output_palette = make_output_palette(adjusted, scene_palette, palette_config)
    confidence = float(min(1.0, max(best_share, best_score)))
    return PaletteResult(
        color=adjusted,
        confidence=confidence,
        pixel_count=int(mask.sum()),
        palette=output_palette,
    )


def make_output_palette(
    base_color: RGB,
    scene_palette: tuple[RGB, ...],
    palette_config: PaletteConfig,
) -> tuple[RGB, ...]:
    size = max(1, int(palette_config.palette_size))
    mode = palette_config.multi_color_mode.lower().strip()

    if mode == "harmonic":
        palette = _harmonic_palette(base_color, size, palette_config.harmony_strength)
    elif mode == "cinematic":
        source = scene_palette or _harmonic_palette(base_color, size, palette_config.harmony_strength)
        palette = tuple(
            color.adjust_hsv(saturation_multiplier=0.88, brightness_multiplier=0.78)
            for color in _fill_palette(base_color, source, size, palette_config.harmony_strength)
        )
    else:
        palette = _fill_palette(base_color, scene_palette, size, palette_config.harmony_strength)

    return palette[:size]


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


def _resize_image(rgb_image: np.ndarray, width: int, height: int) -> np.ndarray:
    target_width = max(16, int(width))
    target_height = max(16, int(height))
    h, w = rgb_image.shape[:2]
    if w == target_width and h == target_height:
        return rgb_image
    return cv2.resize(rgb_image, (target_width, target_height), interpolation=cv2.INTER_AREA)


def _scene_elegance_score(saturation: np.ndarray, value: np.ndarray) -> float:
    if saturation.size == 0 or value.size == 0:
        return 0.0
    mean_sat = float(np.mean(saturation))
    mean_val = float(np.mean(value))
    # Reward colors that are vivid enough to read as ambient lighting without
    # being fully clipped white or harshly oversaturated.
    sat_balance = 1.0 - min(1.0, abs(mean_sat - 0.62) / 0.62)
    val_balance = 1.0 - min(1.0, abs(mean_val - 0.58) / 0.58)
    return max(0.0, min(1.0, sat_balance * 0.55 + val_balance * 0.45))


def _dedupe_palette(colors: list[RGB], size: int) -> tuple[RGB, ...]:
    palette: list[RGB] = []
    for color in colors:
        if all(color.distance(existing) >= 28 for existing in palette):
            palette.append(color)
        if len(palette) >= size:
            break
    return tuple(palette)


def _fill_palette(
    base_color: RGB,
    scene_palette: tuple[RGB, ...],
    size: int,
    harmony_strength: float,
) -> tuple[RGB, ...]:
    colors = list(_dedupe_palette([base_color, *scene_palette], size))
    if len(colors) < size:
        for color in _harmonic_palette(base_color, size, harmony_strength):
            if all(color.distance(existing) >= 18 for existing in colors):
                colors.append(color)
            if len(colors) >= size:
                break
    while len(colors) < size:
        colors.append(base_color)
    return tuple(colors[:size])


def _harmonic_palette(base_color: RGB, size: int, harmony_strength: float) -> tuple[RGB, ...]:
    r, g, b = (channel / 255.0 for channel in base_color.to_tuple())
    hue, saturation, value = colorsys.rgb_to_hsv(r, g, b)
    spread = max(0.05, min(0.50, float(harmony_strength))) * 0.22
    if size <= 1:
        offsets = [0.0]
    elif size == 2:
        offsets = [-spread, spread]
    else:
        offsets = np.linspace(-spread, spread, size).tolist()
    colors: list[RGB] = []
    for offset in offsets:
        rr, gg, bb = colorsys.hsv_to_rgb(
            (hue + offset) % 1.0,
            max(0.0, min(1.0, saturation * 0.94)),
            max(0.0, min(1.0, value)),
        )
        colors.append(RGB(rr * 255.0, gg * 255.0, bb * 255.0))
    return tuple(colors)

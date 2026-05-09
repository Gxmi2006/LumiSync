from __future__ import annotations

import logging

import cv2
import numpy as np

from lumisync.core.config import VisualPriorityConfig

LOGGER = logging.getLogger(__name__)


class SaliencyDetector:
    """Lightweight visual saliency detector built from OpenCV primitives."""

    def __init__(self, config: VisualPriorityConfig) -> None:
        self.config = config

    def update_config(self, config: VisualPriorityConfig) -> None:
        self.config = config

    def compute(self, rgb_image: np.ndarray) -> np.ndarray:
        if rgb_image.size == 0:
            return np.zeros((1, 1), dtype=np.float32)

        method = self.config.saliency_method.lower()
        if method == "spectral_residual":
            saliency = self._spectral_residual(rgb_image)
        else:
            saliency = self._hybrid_saliency(rgb_image)

        sensitivity = max(0.1, float(self.config.saliency_sensitivity))
        saliency = np.clip(saliency * sensitivity, 0.0, 1.0)
        return cv2.GaussianBlur(saliency.astype(np.float32), (0, 0), 1.0)

    def _hybrid_saliency(self, rgb_image: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0

        saturation = hsv[:, :, 1].astype(np.float32) / 255.0
        value = hsv[:, :, 2].astype(np.float32) / 255.0

        local_mean = cv2.GaussianBlur(gray, (0, 0), 3.0)
        local_contrast = np.abs(gray - local_mean)
        local_contrast = _normalize01(local_contrast)

        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge = _normalize01(cv2.magnitude(sobel_x, sobel_y))

        bright_sat = _normalize01((value ** 1.4) * (saturation ** 1.2))
        glow = cv2.GaussianBlur(bright_sat, (0, 0), 4.0)
        glow = _normalize01(glow * bright_sat)

        spectral = self._spectral_residual(rgb_image)
        combined = (
            local_contrast * 0.24
            + edge * 0.18
            + bright_sat * 0.26
            + glow * 0.22
            + spectral * 0.10
        )
        return _normalize01(combined)

    def _spectral_residual(self, rgb_image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
        try:
            saliency_api = getattr(cv2, "saliency", None)
            if saliency_api is not None:
                detector = saliency_api.StaticSaliencySpectralResidual_create()
                ok, saliency = detector.computeSaliency(rgb_image)
                if ok:
                    return _normalize01(saliency.astype(np.float32))
        except Exception:
            LOGGER.debug("OpenCV saliency module failed; using local spectral residual", exc_info=True)

        gray32 = gray.astype(np.float32) / 255.0
        dft = cv2.dft(gray32, flags=cv2.DFT_COMPLEX_OUTPUT)
        magnitude, angle = cv2.cartToPolar(dft[:, :, 0], dft[:, :, 1])
        log_amplitude = np.log(np.maximum(magnitude, 1e-6))
        smooth = cv2.blur(log_amplitude, (3, 3))
        residual = log_amplitude - smooth
        exp_residual = np.exp(residual)
        real, imag = cv2.polarToCart(exp_residual, angle)
        inverse = cv2.idft(np.dstack([real, imag]))
        saliency = inverse[:, :, 0] ** 2 + inverse[:, :, 1] ** 2
        saliency = cv2.GaussianBlur(saliency, (0, 0), 2.5)
        return _normalize01(saliency)


def _normalize01(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float32, copy=False)
    min_value = float(values.min())
    max_value = float(values.max())
    span = max_value - min_value
    if span <= 1e-6:
        return np.zeros_like(values, dtype=np.float32)
    return (values - min_value) / span

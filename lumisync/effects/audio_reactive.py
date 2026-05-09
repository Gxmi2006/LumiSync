from __future__ import annotations

import logging
import time

from lumisync.core.config import AudioPulseConfig

LOGGER = logging.getLogger(__name__)


class AudioPulseProvider:
    def __init__(self, config: AudioPulseConfig) -> None:
        self.config = config
        self._meter = None
        self._last_probe = 0.0
        self._level = 0.0
        self._last_time = time.monotonic()
        self._available = True

    def update_config(self, config: AudioPulseConfig) -> None:
        self.config = config
        if not config.enabled:
            self._meter = None

    def multiplier(self) -> float:
        if not self.config.enabled:
            return 1.0

        raw = self._read_peak()
        now = time.monotonic()
        dt = max(0.001, now - self._last_time)
        self._last_time = now

        coefficient = self.config.attack if raw > self._level else self.config.release
        coefficient = max(0.01, min(1.0, coefficient))
        self._level += (raw - self._level) * min(1.0, coefficient * dt * 30.0)
        return 1.0 + max(0.0, self.config.strength) * self._level

    def _read_peak(self) -> float:
        if not self._available:
            return 0.0
        if self._meter is None and time.monotonic() - self._last_probe > 1.0:
            self._last_probe = time.monotonic()
            self._meter = self._find_meter()
        if self._meter is None:
            return 0.0
        try:
            return max(0.0, min(1.0, float(self._meter.GetPeakValue())))
        except Exception as exc:
            LOGGER.debug("Audio peak read failed: %s", exc)
            self._meter = None
            return 0.0

    def _find_meter(self) -> object | None:
        try:
            from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
        except Exception as exc:
            LOGGER.warning("pycaw unavailable; audio pulsing disabled: %s", exc)
            self._available = False
            return None

        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                process = getattr(session, "Process", None)
                if self.config.spotify_only:
                    if process is None or process.name().lower() != "spotify.exe":
                        continue
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                LOGGER.info("Using audio peak meter from %s", process.name() if process else "system")
                return meter
        except Exception as exc:
            LOGGER.debug("Audio meter discovery failed: %s", exc)
        return None


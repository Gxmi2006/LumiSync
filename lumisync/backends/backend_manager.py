from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
import socket
import time
from typing import Iterable

from lumisync.core.color import RGB
from lumisync.core.config import AuraConfig, Config, OpenRgbConfig, RgbConfig

LOGGER = logging.getLogger(__name__)


class ControllerUnavailable(RuntimeError):
    def __init__(self, message: str, status: str = "unavailable") -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True, slots=True)
class BackendProbeResult:
    key: str
    label: str
    status: str
    detail: str
    device_count: int = 0

    @property
    def connected(self) -> bool:
        return self.status in {"available", "connected"}

    def line(self) -> str:
        suffix = f" - {self.detail}" if self.detail else ""
        if self.device_count:
            suffix += f" ({self.device_count} device(s))"
        return f"{self.label}: {self.status}{suffix}"


@dataclass(frozen=True, slots=True)
class BackendStatusReport:
    aura: BackendProbeResult
    openrgb: BackendProbeResult
    active_backend: str

    def lines(self) -> list[str]:
        return [
            "LumiSync backend status:",
            f"  {self.aura.line()}",
            f"  {self.openrgb.line()}",
            f"  Active backend: {self.active_backend}",
        ]

    def to_text(self) -> str:
        return "\n".join(self.lines())


@dataclass(slots=True)
class ControllerState:
    key: str
    name: str
    connected: bool = False
    last_error: str | None = None


class RgbController(ABC):
    backend_key = "unknown"
    report_label = "Unknown"
    success_status = "available"

    def __init__(self, rgb_config: RgbConfig) -> None:
        self.rgb_config = rgb_config
        self.state = ControllerState(key=self.backend_key, name=self.name)
        self._last_color: RGB | None = None
        self._last_update = 0.0

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    def device_count(self) -> int:
        return 0

    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    def set_color(self, color: RGB, region_colors: tuple[RGB, ...] = ()) -> bool:
        now = time.monotonic()
        min_interval = self.rgb_config.minimum_update_interval_ms / 1000.0
        if now - self._last_update < min_interval:
            return False
        if (
            self._last_color is not None
            and color.distance(self._last_color) < self.rgb_config.minimum_color_delta
        ):
            return False
        self._apply_color(color, region_colors)
        self._last_update = now
        self._last_color = color
        return True

    @abstractmethod
    def _apply_color(self, color: RGB, region_colors: tuple[RGB, ...]) -> None:
        raise NotImplementedError


class AuraController(RgbController):
    backend_key = "aura"
    report_label = "Aura"
    success_status = "available"

    DEVTYPE_ALL = 0x00000000
    DEVTYPE_KEYBOARD = 0x00080000
    DEVTYPE_KEYBOARD_5ZONE = 0x00080001
    DEVTYPE_NBKEYBOARD = 0x00081000
    DEVTYPE_NBKEYBOARD4ZONE = 0x00081001

    DEVICE_TYPE_NAMES = {
        "all": DEVTYPE_ALL,
        "keyboard": DEVTYPE_KEYBOARD,
        "keyboard_5zone": DEVTYPE_KEYBOARD_5ZONE,
        "notebook_keyboard": DEVTYPE_NBKEYBOARD,
        "notebook_keyboard_4zone": DEVTYPE_NBKEYBOARD4ZONE,
    }

    def __init__(self, rgb_config: RgbConfig, aura_config: AuraConfig) -> None:
        super().__init__(rgb_config)
        self.aura_config = aura_config
        self._pythoncom = None
        self._sdk = None
        self._devices: list[object] = []

    @property
    def name(self) -> str:
        return "ASUS Aura SDK"

    @property
    def device_count(self) -> int:
        return len(self._devices)

    def connect(self) -> None:
        LOGGER.info("Checking Aura backend")
        if not self.aura_config.enabled:
            raise ControllerUnavailable("Aura backend disabled in config", "disabled")

        try:
            import pythoncom
            import win32com.client
        except Exception as exc:
            raise ControllerUnavailable(
                f"pywin32 COM support is not installed or cannot be imported: {exc}",
                "not found",
            ) from exc

        try:
            pythoncom.CoInitialize()
            self._pythoncom = pythoncom
            LOGGER.info("Aura COM support loaded; creating aura.sdk.1 COM object")
            self._sdk = win32com.client.Dispatch("aura.sdk.1")
        except Exception as exc:
            self.close()
            raise ControllerUnavailable(
                f"Aura SDK COM object aura.sdk.1 was not found or could not start: {exc}",
                "not found",
            ) from exc

        try:
            LOGGER.info("Aura SDK object created; switching device control mode")
            self._sdk.SwitchMode()
            self._devices = self._enumerate_devices()
        except ControllerUnavailable:
            self.close()
            raise
        except Exception as exc:
            self.close()
            raise ControllerUnavailable(
                f"Aura SDK initialized but failed during device discovery: {exc}",
                "error",
            ) from exc

        if not self._devices:
            self.close()
            raise ControllerUnavailable(
                "Aura SDK is installed, but it reported no supported keyboard lighting devices",
                "no devices",
            )

        self.state.connected = True
        self.state.last_error = None
        LOGGER.info("Aura backend available with %s keyboard device(s)", len(self._devices))

    def close(self) -> None:
        try:
            if self._sdk is not None and hasattr(self._sdk, "ReleaseControl"):
                self._sdk.ReleaseControl(0)
        except Exception:
            LOGGER.debug("Aura ReleaseControl failed", exc_info=True)
        self._devices = []
        self._sdk = None
        self.state.connected = False
        if self._pythoncom is not None:
            try:
                self._pythoncom.CoUninitialize()
            except Exception:
                LOGGER.debug("Aura COM uninitialize failed", exc_info=True)
            self._pythoncom = None

    def _enumerate_devices(self) -> list[object]:
        if self._sdk is None:
            raise ControllerUnavailable("Aura SDK object is not initialized", "not found")

        wanted_types = [
            self.DEVICE_TYPE_NAMES[name]
            for name in self.aura_config.device_types
            if name in self.DEVICE_TYPE_NAMES
        ]
        devices: list[object] = []
        seen: set[str] = set()

        for device_type in wanted_types or [self.DEVTYPE_NBKEYBOARD, self.DEVTYPE_NBKEYBOARD4ZONE]:
            try:
                LOGGER.info("Aura: enumerating device type %#x", device_type)
                collection = self._sdk.Enumerate(device_type)
                for device in collection:
                    key = f"{getattr(device, 'Type', '')}:{getattr(device, 'Name', '')}"
                    if key not in seen:
                        devices.append(device)
                        seen.add(key)
            except Exception as exc:
                LOGGER.info("Aura: device type %#x unavailable: %s", device_type, exc)

        if not devices:
            try:
                LOGGER.info("Aura: trying all-device enumeration as fallback")
                for device in self._sdk.Enumerate(self.DEVTYPE_ALL):
                    name = str(getattr(device, "Name", "")).lower()
                    dev_type = int(getattr(device, "Type", 0))
                    if dev_type in wanted_types or "keyboard" in name or "tuf" in name:
                        devices.append(device)
            except Exception as exc:
                LOGGER.info("Aura: all-device enumeration failed: %s", exc)

        if devices:
            names = ", ".join(str(getattr(device, "Name", "unknown")) for device in devices)
            LOGGER.info("Aura: matched keyboard device(s): %s", names)
        else:
            LOGGER.info("Aura: no keyboard lighting devices matched configured device types")
        return devices

    def _apply_color(self, color: RGB, region_colors: tuple[RGB, ...]) -> None:
        if not self._devices:
            raise RuntimeError("Aura backend has no active keyboard devices")

        packed = _aura_color(color)
        gradient = [_aura_color(entry) for entry in region_colors] if region_colors else []
        for device in list(self._devices):
            try:
                lights = device.Lights
                count = int(lights.Count)
                for idx in range(count):
                    selected = packed
                    if gradient:
                        selected = gradient[
                            min(len(gradient) - 1, idx * len(gradient) // max(1, count))
                        ]
                    lights(idx).Color = selected
                device.Apply()
            except Exception as exc:
                self.state.connected = False
                self.state.last_error = str(exc)
                raise


class OpenRgbController(RgbController):
    backend_key = "openrgb"
    report_label = "OpenRGB"
    success_status = "connected"

    def __init__(self, rgb_config: RgbConfig, openrgb_config: OpenRgbConfig) -> None:
        super().__init__(rgb_config)
        self.openrgb_config = openrgb_config
        self._client = None
        self._devices: list[object] = []
        self._rgb_color_class = None

    @property
    def name(self) -> str:
        return "OpenRGB SDK"

    @property
    def device_count(self) -> int:
        return len(self._devices)

    def connect(self) -> None:
        LOGGER.info("Checking OpenRGB backend")
        if not self.openrgb_config.enabled:
            raise ControllerUnavailable("OpenRGB backend disabled in config", "disabled")

        try:
            from openrgb import OpenRGBClient
            from openrgb.utils import RGBColor
        except Exception as exc:
            raise ControllerUnavailable(
                f"openrgb-python is not installed or cannot be imported: {exc}",
                "not found",
            ) from exc

        self._wait_for_server()

        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(max(0.1, float(self.openrgb_config.socket_timeout_seconds)))
        try:
            LOGGER.info(
                "OpenRGB server reachable; connecting SDK client to %s:%s",
                self.openrgb_config.address,
                self.openrgb_config.port,
            )
            self._client = OpenRGBClient(
                self.openrgb_config.address,
                self.openrgb_config.port,
                self.openrgb_config.client_name,
            )
            self._rgb_color_class = RGBColor
            self._devices = self._select_devices(self._client.devices)
            if self.openrgb_config.set_custom_mode:
                self._set_custom_mode_on_devices()
        except Exception as exc:
            self.close()
            status = _openrgb_status_from_exception(exc)
            raise ControllerUnavailable(
                f"OpenRGB SDK server was reachable, but client setup failed: {exc}",
                status,
            ) from exc
        finally:
            socket.setdefaulttimeout(old_timeout)

        if not self._devices:
            self.close()
            raise ControllerUnavailable(
                "OpenRGB connected, but no usable RGB device was selected",
                "no devices",
            )

        self.state.connected = True
        self.state.last_error = None
        names = ", ".join(str(getattr(device, "name", device)) for device in self._devices)
        LOGGER.info("OpenRGB backend connected with device(s): %s", names)

    def close(self) -> None:
        try:
            if self._client is not None and hasattr(self._client, "disconnect"):
                self._client.disconnect()
        except Exception:
            LOGGER.debug("OpenRGB disconnect failed", exc_info=True)
        self._client = None
        self._devices = []
        self.state.connected = False

    def _wait_for_server(self) -> None:
        timeout = max(0.1, float(self.openrgb_config.connection_timeout_seconds))
        retry_interval = max(0.05, float(self.openrgb_config.retry_interval_seconds))
        socket_timeout = max(0.05, float(self.openrgb_config.socket_timeout_seconds))
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        last_status = "timeout"

        LOGGER.info(
            "OpenRGB: probing SDK server at %s:%s for up to %.2fs",
            self.openrgb_config.address,
            self.openrgb_config.port,
            timeout,
        )
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                detail = f"last error: {last_error}" if last_error else "no response"
                raise ControllerUnavailable(
                    f"OpenRGB SDK server probe ended with {last_status}; {detail}",
                    last_status,
                )

            try:
                with socket.create_connection(
                    (self.openrgb_config.address, self.openrgb_config.port),
                    timeout=min(socket_timeout, remaining),
                ):
                    LOGGER.info("OpenRGB: SDK server port is reachable")
                    return
            except OSError as exc:
                last_error = exc
                last_status = _openrgb_status_from_exception(exc)
                LOGGER.info("OpenRGB: server probe failed (%s): %s", last_status, exc)
                time.sleep(min(retry_interval, max(0.0, deadline - time.monotonic())))

    def _set_custom_mode_on_devices(self) -> None:
        for device in self._devices:
            if hasattr(device, "set_custom_mode"):
                try:
                    device.set_custom_mode()
                except Exception:
                    LOGGER.debug("OpenRGB set_custom_mode failed for %s", device, exc_info=True)

    def _select_devices(self, devices: Iterable[object]) -> list[object]:
        all_devices = list(devices)
        if not all_devices:
            LOGGER.info("OpenRGB: server connected but reported no devices")
            return []

        if not self.rgb_config.prefer_keyboard_devices:
            LOGGER.info(
                "OpenRGB: using all %s device(s) because prefer_keyboard_devices=false",
                len(all_devices),
            )
            return all_devices

        selected = [device for device in all_devices if self._looks_like_keyboard(device)]
        if selected:
            LOGGER.info("OpenRGB: selected %s preferred device(s)", len(selected))
            return selected
        if self.openrgb_config.allow_all_devices_if_no_keyboard:
            LOGGER.warning(
                "OpenRGB: no preferred device matched; using all %s device(s) because config allows it",
                len(all_devices),
            )
            return all_devices
        LOGGER.info("OpenRGB: no preferred devices matched configured names/types")
        return []

    def _looks_like_keyboard(self, device: object) -> bool:
        name = str(getattr(device, "name", "")).lower()
        configured = [entry.lower() for entry in self.rgb_config.device_name_contains]
        if any(entry and entry in name for entry in configured):
            return True

        device_type = getattr(device, "type", None)
        type_text = str(device_type).lower()
        return "keyboard" in type_text

    def _apply_color(self, color: RGB, region_colors: tuple[RGB, ...]) -> None:
        if self._rgb_color_class is None:
            raise RuntimeError("OpenRGB RGBColor class is not initialized")
        if not self._devices:
            raise RuntimeError("OpenRGB backend has no active keyboard devices")

        for device in list(self._devices):
            try:
                if region_colors:
                    self._apply_gradient_to_device(device, region_colors)
                else:
                    self._set_openrgb_object_color(device, color)
            except Exception as exc:
                self.state.connected = False
                self.state.last_error = str(exc)
                raise

    def _apply_gradient_to_device(self, device: object, region_colors: tuple[RGB, ...]) -> None:
        zones = list(getattr(device, "zones", []) or [])
        if zones:
            for idx, zone in enumerate(zones):
                color = region_colors[
                    min(len(region_colors) - 1, idx * len(region_colors) // max(1, len(zones)))
                ]
                self._set_openrgb_object_color(zone, color)
            return

        leds = list(getattr(device, "leds", []) or [])
        if leds:
            for idx, led in enumerate(leds):
                color = region_colors[
                    min(len(region_colors) - 1, idx * len(region_colors) // max(1, len(leds)))
                ]
                self._set_openrgb_object_color(led, color)
            return

        self._set_openrgb_object_color(device, region_colors[0])

    def _set_openrgb_object_color(self, target: object, color: RGB) -> None:
        rgb = self._rgb_color_class(color.r, color.g, color.b)
        try:
            target.set_color(rgb, fast=True)
        except TypeError:
            target.set_color(rgb)


class NoopController(RgbController):
    backend_key = "software fallback"
    report_label = "Software fallback"
    success_status = "active"

    @property
    def name(self) -> str:
        return "Software fallback"

    def connect(self) -> None:
        self.state.connected = True
        self.state.last_error = None
        LOGGER.warning(
            "Software fallback active: capture and color extraction will run, "
            "but no hardware RGB updates will be sent"
        )

    def close(self) -> None:
        self.state.connected = False

    def set_color(self, color: RGB, region_colors: tuple[RGB, ...] = ()) -> bool:
        self._last_color = color
        self._apply_color(color, region_colors)
        return False

    def _apply_color(self, color: RGB, region_colors: tuple[RGB, ...]) -> None:
        LOGGER.debug("Software fallback color update: %s", color.to_hex())


class ControllerManager:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.controller: RgbController | None = None
        self._last_attempt = 0.0
        self.last_report: BackendStatusReport | None = None
        self.active_backend = "none"

    @property
    def name(self) -> str:
        return self.active_backend

    def initialize(self) -> BackendStatusReport:
        report = self._probe_backends()
        self.last_report = report
        self.log_status_report(report)
        return report

    def log_status_report(self, report: BackendStatusReport) -> None:
        for line in report.lines():
            LOGGER.info(line)

    def update_config(self, config: Config) -> None:
        self.config = config
        if self.controller:
            self.controller.rgb_config = config.rgb
        self.close()
        self.initialize()

    def close(self) -> None:
        if self.controller:
            self.controller.close()
        self.controller = None
        self.active_backend = "none"

    def ensure_connected(self, force: bool = False) -> RgbController:
        now = time.monotonic()
        if (
            self.controller
            and self.controller.state.connected
            and not isinstance(self.controller, NoopController)
        ):
            return self.controller
        if (
            self.controller
            and self.controller.state.connected
            and isinstance(self.controller, NoopController)
            and not force
            and now - self._last_attempt < self.config.rgb.reconnect_interval_seconds
        ):
            return self.controller
        if not force and now - self._last_attempt < 2.0:
            raise ControllerUnavailable("Waiting before next RGB reconnect attempt", "retry wait")

        report = self._probe_backends()
        self.last_report = report
        return self.controller or self._activate_fallback("software fallback")

    def set_color(self, color: RGB, region_colors: tuple[RGB, ...] = ()) -> bool:
        try:
            controller = self.ensure_connected()
        except ControllerUnavailable as exc:
            LOGGER.debug("RGB backend not connected yet: %s", exc)
            return False
        try:
            return controller.set_color(color, region_colors)
        except Exception as exc:
            LOGGER.warning("RGB update failed on %s: %s", controller.name, exc)
            controller.state.connected = False
            controller.state.last_error = str(exc)
            return False

    def _probe_backends(self) -> BackendStatusReport:
        self._last_attempt = time.monotonic()
        self.close()

        active_controller: RgbController | None = None
        choice = self.config.app.controller.lower()

        aura_result = self._skipped_result("aura", "Aura", choice)
        openrgb_result = self._skipped_result("openrgb", "OpenRGB", choice)
        aura_controller: RgbController | None = None
        openrgb_controller: RgbController | None = None

        if self._selection_allows("openrgb", choice):
            openrgb_result, openrgb_controller = self._probe_controller(
                OpenRgbController(self.config.rgb, self.config.openrgb)
            )

        if self._selection_allows("aura", choice):
            aura_result, aura_controller = self._probe_controller(
                AuraController(self.config.rgb, self.config.aura)
            )

        if openrgb_controller and self._selection_allows("openrgb", choice):
            active_controller = openrgb_controller
            if aura_controller:
                aura_controller.close()
        elif aura_controller and self._selection_allows("aura", choice):
            active_controller = aura_controller
            if openrgb_controller:
                openrgb_controller.close()
        else:
            if aura_controller:
                aura_controller.close()
            if openrgb_controller:
                openrgb_controller.close()

        if active_controller is not None:
            self.controller = active_controller
            self.active_backend = active_controller.backend_key
            LOGGER.info("Active RGB backend selected: %s", self.active_backend)
        else:
            fallback_name = "none" if choice in {"none", "noop", "debug"} else "software fallback"
            self._activate_fallback(fallback_name)

        return BackendStatusReport(
            aura=aura_result,
            openrgb=openrgb_result,
            active_backend=self.active_backend,
        )

    @staticmethod
    def _skipped_result(backend_key: str, label: str, choice: str) -> BackendProbeResult:
        return BackendProbeResult(
            key=backend_key,
            label=label,
            status="disabled",
            detail=f"Skipped because app.controller is {choice!r}",
        )

    def _probe_controller(
        self,
        controller: RgbController,
    ) -> tuple[BackendProbeResult, RgbController | None]:
        choice = self.config.app.controller.lower()
        if not self._selection_allows(controller.backend_key, choice):
            detail = f"Skipped because app.controller is {self.config.app.controller!r}"
            result = BackendProbeResult(
                key=controller.backend_key,
                label=controller.report_label,
                status="disabled",
                detail=detail,
            )
            LOGGER.info("%s backend skipped: %s", controller.report_label, detail)
            return result, None

        try:
            controller.connect()
            result = BackendProbeResult(
                key=controller.backend_key,
                label=controller.report_label,
                status=controller.success_status,
                detail="ready for hardware RGB updates",
                device_count=controller.device_count,
            )
            return result, controller
        except ControllerUnavailable as exc:
            controller.close()
            result = BackendProbeResult(
                key=controller.backend_key,
                label=controller.report_label,
                status=exc.status,
                detail=str(exc),
            )
            LOGGER.info(
                "%s backend unavailable: status=%s detail=%s",
                controller.report_label,
                exc.status,
                exc,
            )
            return result, None
        except Exception as exc:
            controller.close()
            LOGGER.exception("%s backend probe crashed safely", controller.report_label)
            result = BackendProbeResult(
                key=controller.backend_key,
                label=controller.report_label,
                status="error",
                detail=str(exc),
            )
            return result, None

    def _activate_fallback(self, active_name: str) -> NoopController:
        fallback = NoopController(self.config.rgb)
        fallback.connect()
        self.controller = fallback
        self.active_backend = active_name
        LOGGER.info("Active RGB backend selected: %s", self.active_backend)
        return fallback

    @staticmethod
    def _selection_allows(backend_key: str, choice: str) -> bool:
        if choice in {"auto", "openrgb"}:
            return backend_key == "openrgb"
        if choice in {"aura", "asus", "armoury", "armoury_crate"}:
            return backend_key == "aura"
        return False


def _openrgb_status_from_exception(exc: BaseException) -> str:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, ConnectionRefusedError):
        return "not running"
    winerror = getattr(exc, "winerror", None)
    errno = getattr(exc, "errno", None)
    if winerror in {10061} or errno in {10061, 111, 61}:
        return "not running"
    if winerror in {10060, 10065, 10051, 10049}:
        return "timeout"
    return "not running"


def _aura_color(color: RGB) -> int:
    return (color.b << 16) | (color.g << 8) | color.r


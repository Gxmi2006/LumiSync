from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from pathlib import Path
import os
import shutil
import sys
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


APP_DIR_NAME = "LumiSync"


@dataclass(slots=True)
class AppConfig:
    fps: int = 20
    controller: str = "auto"
    capture_mode: str = "active_window"
    debug_overlay: bool = False
    tray_icon: bool = True
    manage_startup_from_config: bool = False
    log_level: str = "INFO"


@dataclass(slots=True)
class HotkeyConfig:
    pause_resume: str = "ctrl+alt+p"
    reload_config: str = "ctrl+alt+r"
    quit: str = "ctrl+alt+q"
    toggle_debug: str = "ctrl+alt+d"


@dataclass(slots=True)
class WindowConfig:
    process_name: str = ""
    title_contains: str = ""
    redetect_interval_seconds: float = 1.0
    min_client_width: int = 480
    min_client_height: int = 320


@dataclass(slots=True)
class CaptureConfig:
    left_ratio: float = 0.18
    top_ratio: float = 0.12
    width_ratio: float = 0.80
    height_ratio: float = 0.78
    left_offset: int = 0
    top_offset: int = 0
    width_offset: int = 0
    height_offset: int = 0
    min_width: int = 96
    min_height: int = 72


@dataclass(slots=True)
class ProcessingConfig:
    downscale_width: int = 160
    downscale_height: int = 90
    black_threshold: int = 28
    saturation_threshold: int = 40
    quantization_bins: int = 16
    saturation_multiplier: float = 1.15
    brightness_multiplier: float = 0.90
    minimum_mask_pixels: int = 24


@dataclass(slots=True)
class VisualPriorityConfig:
    enabled: bool = True
    saliency_method: str = "hybrid"  # hybrid, spectral_residual
    saliency_sensitivity: float = 1.15
    saliency_threshold: float = 0.34
    min_region_area_ratio: float = 0.0025
    max_region_area_ratio: float = 0.55
    max_regions: int = 8
    selected_regions: int = 3
    saturation_weight: float = 1.35
    brightness_weight: float = 1.00
    contrast_weight: float = 0.85
    glow_weight: float = 1.25
    edge_weight: float = 0.55
    size_weight: float = 0.45
    center_weight: float = 0.70
    motion_weight: float = 0.25
    temporal_weight: float = 0.35
    region_padding_ratio: float = 0.035
    color_percentile: float = 0.72
    saturation_power: float = 1.8
    brightness_power: float = 1.25
    use_kmeans: bool = False
    kmeans_clusters: int = 3
    debug_regions: bool = True
    debug_saliency_map: bool = True
    debug_palette: bool = True


@dataclass(slots=True)
class SmoothingConfig:
    strength: float = 0.62
    minimum_step: int = 1


@dataclass(slots=True)
class RgbConfig:
    minimum_update_interval_ms: int = 16
    minimum_color_delta: float = 2.0
    reconnect_interval_seconds: float = 15.0
    prefer_keyboard_devices: bool = True
    device_name_contains: list[str] = field(
        default_factory=lambda: ["keyboard", "aura", "asus", "tuf"]
    )


@dataclass(slots=True)
class AuraConfig:
    enabled: bool = True
    device_types: list[str] = field(
        default_factory=lambda: [
            "notebook_keyboard",
            "notebook_keyboard_4zone",
            "keyboard",
            "keyboard_5zone",
        ]
    )


@dataclass(slots=True)
class OpenRgbConfig:
    enabled: bool = True
    address: str = "127.0.0.1"
    port: int = 6742
    client_name: str = "LumiSync"
    connection_timeout_seconds: float = 1.5
    retry_interval_seconds: float = 0.25
    socket_timeout_seconds: float = 0.35
    set_custom_mode: bool = True
    allow_all_devices_if_no_keyboard: bool = False


@dataclass(slots=True)
class AudioPulseConfig:
    enabled: bool = False
    strength: float = 0.18
    attack: float = 0.45
    release: float = 0.12
    spotify_only: bool = True


@dataclass(slots=True)
class GradientConfig:
    enabled: bool = False
    regions: int = 3
    mode: str = "horizontal"
    send_regions_to_zones: bool = False


@dataclass(slots=True)
class DiagnosticsConfig:
    write_startup_report: bool = True
    include_monitor_report: bool = True
    include_backend_report: bool = True
    probe_all_backends: bool = False


@dataclass(slots=True)
class LoggingConfig:
    level: str = "INFO"
    file: str = "%APPDATA%/LumiSync/logs/lumisync.log"
    max_bytes: int = 1_000_000
    backup_count: int = 3


@dataclass(slots=True)
class StartupConfig:
    enabled: bool = False
    shortcut_name: str = "LumiSync.lnk"


@dataclass(slots=True)
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    window: WindowConfig = field(default_factory=WindowConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    visual_priority: VisualPriorityConfig = field(default_factory=VisualPriorityConfig)
    smoothing: SmoothingConfig = field(default_factory=SmoothingConfig)
    rgb: RgbConfig = field(default_factory=RgbConfig)
    aura: AuraConfig = field(default_factory=AuraConfig)
    openrgb: OpenRgbConfig = field(default_factory=OpenRgbConfig)
    audio_pulse: AudioPulseConfig = field(default_factory=AudioPulseConfig)
    gradient: GradientConfig = field(default_factory=GradientConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    startup: StartupConfig = field(default_factory=StartupConfig)


T = TypeVar("T")


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / f".{APP_DIR_NAME}"


def default_config_path() -> Path:
    cwd_config = Path.cwd() / "config.toml"
    if cwd_config.exists():
        return cwd_config
    return app_data_dir() / "config.toml"


def ensure_default_config(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    bundled = Path(__file__).resolve().parents[2] / "config.toml"
    if bundled.exists():
        shutil.copy2(bundled, path)
    else:
        path.write_text("", encoding="utf-8")


def load_config(path: Path | None = None) -> Config:
    resolved = path or default_config_path()
    ensure_default_config(resolved)
    with resolved.open("rb") as handle:
        data = tomllib.load(handle)
    return _from_mapping(Config, data)


def _from_mapping(cls: type[T], data: dict[str, Any]) -> T:
    kwargs: dict[str, Any] = {}
    type_hints = get_type_hints(cls)
    for item in fields(cls):
        value = data.get(item.name)
        default_value = _field_default(item)
        if value is None:
            kwargs[item.name] = default_value
            continue
        field_type = type_hints.get(item.name, item.type)
        if is_dataclass(default_value):
            if not isinstance(value, dict):
                raise ValueError(f"Config section [{item.name}] must be a table")
            kwargs[item.name] = _from_mapping(type(default_value), value)
        else:
            kwargs[item.name] = _coerce_value(field_type, value, item.name)
    return cls(**kwargs)


def _field_default(item: Any) -> Any:
    if item.default is not MISSING:
        return item.default
    if item.default_factory is not MISSING:
        return item.default_factory()
    return None


def _coerce_value(expected_type: Any, value: Any, name: str) -> Any:
    origin = get_origin(expected_type)
    if origin in (list, tuple):
        if not isinstance(value, list):
            raise ValueError(f"Config value {name!r} must be a list")
        args = get_args(expected_type)
        if not args:
            return value
        return [_coerce_scalar(args[0], entry, name) for entry in value]
    return _coerce_scalar(expected_type, value, name)


def _coerce_scalar(expected_type: Any, value: Any, name: str) -> Any:
    if expected_type is bool:
        if not isinstance(value, bool):
            raise ValueError(f"Config value {name!r} must be true or false")
        return value
    if expected_type is int:
        if isinstance(value, bool):
            raise ValueError(f"Config value {name!r} must be an integer")
        return int(value)
    if expected_type is float:
        if isinstance(value, bool):
            raise ValueError(f"Config value {name!r} must be a number")
        return float(value)
    if expected_type is str:
        return str(value)
    return value


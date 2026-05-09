from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from pathlib import Path
import math
import os
import shutil
import sys
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


APP_DIR_NAME = "LumiSync"


@dataclass(frozen=True, slots=True)
class ConfigIssue:
    path: str
    message: str
    suggestion: str = ""
    severity: str = "warning"

    def line(self) -> str:
        suffix = f" Fix: {self.suggestion}" if self.suggestion else ""
        return f"{self.severity.upper()} {self.path}: {self.message}.{suffix}"


@dataclass(slots=True)
class AppConfig:
    fps: int = 20
    controller: str = "openrgb"
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
    fullscreen_priority: bool = True


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
    saturation_multiplier: float = 1.05
    brightness_multiplier: float = 0.78
    minimum_mask_pixels: int = 24
    ignore_letterbox_bars: bool = True


@dataclass(slots=True)
class MonitorConfig:
    index: int = 1
    include_taskbar: bool = True
    prefer_primary: bool = True
    edge_sampling: bool = False
    edge_thickness_ratio: float = 0.08


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
    strength: float = 0.76
    minimum_step: int = 1
    transition_curve: str = "exponential"


@dataclass(slots=True)
class RgbConfig:
    minimum_update_interval_ms: int = 16
    minimum_color_delta: float = 2.0
    reconnect_interval_seconds: float = 15.0
    prefer_keyboard_devices: bool = True
    device_name_contains: list[str] = field(
        default_factory=lambda: [
            "keyboard",
            "laptop",
            "asus",
            "tuf",
            "mouse",
            "strip",
            "led",
            "motherboard",
            "gpu",
            "ram",
        ]
    )


@dataclass(slots=True)
class AuraConfig:
    enabled: bool = False
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
    allow_all_devices_if_no_keyboard: bool = True


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
class PaletteConfig:
    fallback_mode: str = "scene_harmony"
    multi_color_mode: str = "cinematic"
    minimum_focal_confidence: float = 0.35
    palette_size: int = 1
    harmony_strength: float = 0.35


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
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
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
    palette: PaletteConfig = field(default_factory=PaletteConfig)
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
    config, _issues = load_config_with_issues(path)
    return config


def load_config_with_issues(path: Path | None = None) -> tuple[Config, list[ConfigIssue]]:
    resolved = path or default_config_path()
    ensure_default_config(resolved)
    with resolved.open("rb") as handle:
        data = tomllib.load(handle)
    config = _from_mapping(Config, data)
    issues = validate_config(config, fix=True)
    return config, issues


def validate_config(config: Config, fix: bool = False) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []

    def issue(path: str, message: str, suggestion: str = "") -> None:
        issues.append(ConfigIssue(path=path, message=message, suggestion=suggestion))

    def set_value(obj: object, attr: str, value: object) -> None:
        if fix:
            setattr(obj, attr, value)

    def clamp_number(
        obj: object,
        attr: str,
        path: str,
        minimum: float,
        maximum: float,
        fallback: float | int,
        integer: bool = False,
    ) -> None:
        raw = getattr(obj, attr)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            issue(path, f"value {raw!r} is not numeric", f"using {fallback!r}")
            set_value(obj, attr, fallback)
            return
        if not math.isfinite(value):
            issue(path, f"value {raw!r} is not finite", f"using {fallback!r}")
            set_value(obj, attr, fallback)
            return
        clamped = max(minimum, min(maximum, value))
        if clamped != value:
            issue(path, f"value {raw!r} is outside {minimum:g}..{maximum:g}", f"using {clamped:g}")
        if integer:
            clamped = int(round(clamped))
        set_value(obj, attr, clamped)

    def choice(obj: object, attr: str, path: str, allowed: set[str], fallback: str) -> None:
        raw = str(getattr(obj, attr)).lower().strip()
        if raw not in allowed:
            issue(path, f"value {raw!r} is unsupported", f"using {fallback!r}")
            set_value(obj, attr, fallback)
        else:
            set_value(obj, attr, raw)

    choice(config.app, "controller", "app.controller", {"openrgb", "auto", "aura", "asus", "armoury", "armoury_crate", "none", "noop", "debug"}, "openrgb")
    choice(config.app, "capture_mode", "app.capture_mode", {"active_window", "window", "monitor", "region"}, "active_window")
    clamp_number(config.app, "fps", "app.fps", 1, 60, 20, integer=True)

    for attr in ("left_ratio", "top_ratio", "width_ratio", "height_ratio"):
        clamp_number(config.capture, attr, f"capture.{attr}", 0.0, 1.0, getattr(CaptureConfig(), attr))
    clamp_number(config.capture, "min_width", "capture.min_width", 16, 7680, 96, integer=True)
    clamp_number(config.capture, "min_height", "capture.min_height", 16, 4320, 72, integer=True)

    clamp_number(config.monitor, "index", "monitor.index", 0, 32, 1, integer=True)
    clamp_number(config.monitor, "edge_thickness_ratio", "monitor.edge_thickness_ratio", 0.01, 0.50, 0.08)

    clamp_number(config.window, "redetect_interval_seconds", "window.redetect_interval_seconds", 0.05, 30.0, 1.0)
    clamp_number(config.window, "min_client_width", "window.min_client_width", 16, 7680, 480, integer=True)
    clamp_number(config.window, "min_client_height", "window.min_client_height", 16, 4320, 320, integer=True)

    clamp_number(config.processing, "downscale_width", "processing.downscale_width", 16, 960, 160, integer=True)
    clamp_number(config.processing, "downscale_height", "processing.downscale_height", 16, 540, 90, integer=True)
    clamp_number(config.processing, "black_threshold", "processing.black_threshold", 0, 254, 28, integer=True)
    clamp_number(config.processing, "saturation_threshold", "processing.saturation_threshold", 0, 254, 36, integer=True)
    clamp_number(config.processing, "quantization_bins", "processing.quantization_bins", 4, 32, 16, integer=True)
    clamp_number(config.processing, "saturation_multiplier", "processing.saturation_multiplier", 0.0, 3.0, 1.05)
    clamp_number(config.processing, "brightness_multiplier", "processing.brightness_multiplier", 0.0, 3.0, 0.78)
    clamp_number(config.processing, "minimum_mask_pixels", "processing.minimum_mask_pixels", 1, 10000, 24, integer=True)

    clamp_number(config.visual_priority, "saliency_sensitivity", "visual_priority.saliency_sensitivity", 0.1, 5.0, 1.15)
    clamp_number(config.visual_priority, "saliency_threshold", "visual_priority.saliency_threshold", 0.0, 0.95, 0.34)
    clamp_number(config.visual_priority, "min_region_area_ratio", "visual_priority.min_region_area_ratio", 0.0001, 0.50, 0.0025)
    clamp_number(config.visual_priority, "max_region_area_ratio", "visual_priority.max_region_area_ratio", 0.01, 0.95, 0.55)
    if config.visual_priority.max_region_area_ratio < config.visual_priority.min_region_area_ratio:
        issue("visual_priority.max_region_area_ratio", "must be greater than min_region_area_ratio", "using min_region_area_ratio")
        set_value(config.visual_priority, "max_region_area_ratio", config.visual_priority.min_region_area_ratio)
    clamp_number(config.visual_priority, "max_regions", "visual_priority.max_regions", 1, 32, 8, integer=True)
    clamp_number(config.visual_priority, "selected_regions", "visual_priority.selected_regions", 1, 16, 3, integer=True)
    clamp_number(config.visual_priority, "color_percentile", "visual_priority.color_percentile", 0.0, 0.98, 0.72)

    clamp_number(config.smoothing, "strength", "smoothing.strength", 0.0, 0.98, 0.76)
    clamp_number(config.smoothing, "minimum_step", "smoothing.minimum_step", 0, 64, 1, integer=True)

    clamp_number(config.rgb, "minimum_update_interval_ms", "rgb.minimum_update_interval_ms", 0, 1000, 16, integer=True)
    clamp_number(config.rgb, "minimum_color_delta", "rgb.minimum_color_delta", 0.0, 120.0, 2.0)
    clamp_number(config.rgb, "reconnect_interval_seconds", "rgb.reconnect_interval_seconds", 1.0, 300.0, 15.0)
    cleaned_device_names = [str(item).strip() for item in config.rgb.device_name_contains if str(item).strip()]
    if len(cleaned_device_names) != len(config.rgb.device_name_contains):
        issue("rgb.device_name_contains", "empty device-name filters were removed", "keep only non-empty strings")
    if fix:
        config.rgb.device_name_contains = cleaned_device_names

    clamp_number(config.openrgb, "port", "openrgb.port", 1, 65535, 6742, integer=True)
    clamp_number(config.openrgb, "connection_timeout_seconds", "openrgb.connection_timeout_seconds", 0.1, 30.0, 1.5)
    clamp_number(config.openrgb, "retry_interval_seconds", "openrgb.retry_interval_seconds", 0.05, 10.0, 0.25)
    clamp_number(config.openrgb, "socket_timeout_seconds", "openrgb.socket_timeout_seconds", 0.05, 10.0, 0.35)

    choice(config.palette, "fallback_mode", "palette.fallback_mode", {"scene_harmony", "dominant"}, "scene_harmony")
    choice(config.palette, "multi_color_mode", "palette.multi_color_mode", {"scene", "harmonic", "cinematic"}, "cinematic")
    clamp_number(config.palette, "minimum_focal_confidence", "palette.minimum_focal_confidence", 0.0, 1.0, 0.35)
    clamp_number(config.palette, "palette_size", "palette.palette_size", 1, 12, 1, integer=True)
    clamp_number(config.palette, "harmony_strength", "palette.harmony_strength", 0.0, 1.0, 0.35)

    clamp_number(config.gradient, "regions", "gradient.regions", 1, 12, 3, integer=True)
    choice(config.gradient, "mode", "gradient.mode", {"horizontal", "vertical"}, "horizontal")

    return issues


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


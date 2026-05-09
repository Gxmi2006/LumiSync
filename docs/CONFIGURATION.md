# Configuration Guide

LumiSync uses TOML because it is human-editable, diff-friendly, and easy to tune while the app is running.

## Core Defaults

```toml
[app]
fps = 20
capture_mode = "active_window"
controller = "openrgb"

[openrgb]
address = "127.0.0.1"
port = 6742
allow_all_devices_if_no_keyboard = true

[aura]
enabled = false
```

OpenRGB is the default path. Aura is legacy/advanced opt-in only.

## Important Sections

- `[app]`: FPS, capture mode, backend preference, tray/overlay toggles.
- `[openrgb]`: SDK Server address, timeouts, custom mode, device fallback.
- `[palette]`: scene harmony fallback and single-color styling.
- `[gradient]`: optional multi-region output, disabled by default.
- `[visual_priority]`: saliency-driven focal region extraction.
- `[monitor]`: monitor index and future monitor sampling settings.
- `[capture]`: normalized region crop and pixel offsets.
- `[window]`: foreground/named window matching.
- `[processing]`: downscale, thresholds, quantization, saturation/brightness.
- `[smoothing]`: transition strength.
- `[rgb]`: update throttling, reconnect interval, preferred device names.

## Scene Harmony

Scene harmony is used when no focal object is strong enough.

```toml
[palette]
fallback_mode = "scene_harmony"
multi_color_mode = "cinematic"
minimum_focal_confidence = 0.35
palette_size = 1
harmony_strength = 0.35
```

Rules of thumb:

- Increase `minimum_focal_confidence` if small highlights win too often.
- Lower it if neon rings, magic effects, or anime highlights are missed.
- Use `palette_size = 3` and enable `[gradient]` later if you want generated gradients.
- Use `multi_color_mode = "scene"` if you want brighter colors sampled directly from the frame.

## Visual Priority

```toml
[visual_priority]
enabled = true
saliency_method = "hybrid"
saliency_threshold = 0.34
selected_regions = 3
glow_weight = 1.25
center_weight = 0.70
temporal_weight = 0.35
debug_regions = true
debug_saliency_map = true
debug_palette = true
```

This mode prioritizes visually important objects over simple frame averages.

White and gray highlights are supported when they are bright, coherent, and salient. Tiny white UI specks are still filtered by region size, center bias, and confidence scoring.

## Config Safety

LumiSync validates runtime config values on load. Unsafe values are clamped to a safe range and reported by:

```powershell
python -m lumisync --setup-check
python -m lumisync --diagnostics
```

Examples:

- `app.fps = 500` is clamped to `60`
- negative capture ratios are clamped to `0.0`
- invalid backend names fall back to `openrgb`
- invalid palette sizes fall back to at least `1`

## Single-Color Output

```toml
[gradient]
enabled = false
regions = 3
mode = "horizontal"
send_regions_to_zones = false

[palette]
palette_size = 1
```

This default keeps the keyboard on one best cinematic scene color. Optional OpenRGB zone gradients can be enabled later by setting `gradient.enabled = true`, `gradient.send_regions_to_zones = true`, and `palette.palette_size = 3`.

## Gaming Profile

```toml
[profiles.gaming]
fps = 30
smoothing_strength = 0.42
brightness_multiplier = 0.92
saturation_multiplier = 1.18
black_threshold = 22
```

Use for games, emulators, and fast content.

## Movie Profile

```toml
[profiles.movie]
fps = 18
capture_mode = "monitor"
smoothing_strength = 0.76
brightness_multiplier = 0.78
black_threshold = 32
cinematic_mode = true
```

Use for films, anime, and streaming apps.

## Low-Power Laptop Profile

```toml
[profiles.low_power_laptop]
fps = 10
downscale_width = 96
downscale_height = 54
smoothing_strength = 0.70
minimum_update_interval_ms = 50
```

Use when on battery or when the machine is under load.

## Compatibility Notes

The typed config loader reads runtime-critical fields and ignores unknown future sections. This lets the repository document stable configuration surfaces before every roadmap item is wired into the loop.

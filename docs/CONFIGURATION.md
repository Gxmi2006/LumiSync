# Configuration Design

LumiSync uses TOML because it is human-editable, diff-friendly, and expressive enough for profiles.

## Core Sections

- `[app]`: runtime mode, FPS, backend preference, tray/overlay toggles.
- `[capture]`: normalized region crop and pixel offsets.
- `[monitor]`: monitor index and future edge sampling options.
- `[window]`: foreground/named window matching.
- `[processing]`: downscale, thresholds, quantization, saturation/brightness.
- `[smoothing]`: transition strength and future curve selection.
- `[rgb]`: update throttling, reconnect interval, device matching.
- `[aura]`: Aura SDK enablement and device types.
- `[openrgb]`: SDK server address, timeouts, and device fallback policy.
- `[effects]`: high-level effect stack toggles.
- `[profiles.*]`: named tuning bundles.

## Defaults

The default config targets active-window ambient sync:

```toml
[app]
fps = 20
capture_mode = "active_window"
controller = "auto"

[window]
process_name = ""
title_contains = ""
```

Blank window filters mean "use the foreground window." Set either field to target a specific app.

## Gaming Profile

```toml
[profiles.gaming]
fps = 30
smoothing_strength = 0.42
brightness_multiplier = 0.92
saturation_multiplier = 1.18
black_threshold = 22
```

Use for games, emulators, and fast content. Lower smoothing improves responsiveness.

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

Use for films, anime, and streaming apps. Higher smoothing prevents distracting flicker.

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

## Cinematic Profile

```toml
[profiles.cinematic]
fps = 16
smoothing_strength = 0.84
adaptive_brightness = true
edge_sampling = true
brightness_multiplier = 0.72
```

Designed for Ambilight-style transitions once edge sampling lands.

## Compatibility Notes

The typed config loader currently reads the runtime-critical fields and ignores unknown future sections. This allows the repository to document stable configuration surfaces before every roadmap item is wired into the loop.

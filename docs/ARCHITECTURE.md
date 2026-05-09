# Architecture

LumiSync is organized as a pipeline. Each stage should have a narrow responsibility and be replaceable without rewriting the whole app.

```text
lumisync/
  core/
    app.py                 main loop, state, lifecycle
    config.py              typed TOML config loader
    color.py               RGB primitive and conversions
    smoothing.py           interpolation engine
    websocket_server.py    optional local API surface
  capture/
    window_capture.py      generic Win32 window discovery
    region_capture.py      MSS rectangle capture
    monitor_detection.py   MSS monitor enumeration
    monitor_capture.py     monitor capture adapter
  processing/
    palette_extraction.py  dominant color and multi-region extraction
  backends/
    backend_manager.py     backend probing, selection, fallback, dispatch
    aura_backend.py        Aura adapter import surface
    openrgb_backend.py     OpenRGB adapter import surface
  effects/
    adaptive_brightness.py brightness normalization
    audio_reactive.py      audio peak brightness pulsing
    effect_pipeline.py     composable color effects
  ui/
    tray.py                tray menu
    hotkeys.py             global hotkeys
  overlays/
    debug_overlay.py       capture diagnostics overlay
  diagnostics/
    diagnostics_report.py  markdown/system status reports
  profiles/
    profile_manager.py     profile loading
  presets/
    __init__.py            future bundled presets
  utils/
    startup.py             Windows Startup shortcut helpers
```

## Runtime Pipeline

1. `core.app` loads config and starts UI helpers.
2. `backends.backend_manager` probes Aura and OpenRGB, then selects a hardware backend or software fallback.
3. `capture.window_capture` selects a foreground/named target window.
4. `capture.region_capture` crops the configured rectangle using MSS.
5. `processing.palette_extraction` downsamples, masks, quantizes, and extracts a dominant color or region palette.
6. `core.smoothing` interpolates between previous and target colors.
7. `effects` optionally modifies brightness or stacks color effects.
8. `backend_manager.set_color()` sends updates only if a backend is connected and throttling allows it.
9. Overlay/tray receive status updates independently of hardware success.

## Backend Abstraction

Backend rules:

- SDK imports and calls must stay inside `lumisync/backends`.
- Aura failure, OpenRGB failure, and no-device states must never stop capture.
- Every backend probe returns a structured status.
- Software fallback must remain valid for development and unsupported hardware.

Current statuses:

- Aura: `available`, `no devices`, `not found`, `disabled`, `error`
- OpenRGB: `connected`, `not running`, `timeout`, `not found`, `no devices`, `disabled`, `error`
- Active backend: `aura`, `openrgb`, `software fallback`, or `none`

## Threading Model

The current loop is intentionally simple: one frame loop performs capture, processing, smoothing, and dispatch with bounded work. Future versions should split work into:

- capture thread: produces latest frame
- processing thread: consumes newest frame only
- dispatch thread: rate-limits backend writes
- UI thread: tray and overlays

The goal is not maximum throughput; it is stable frame pacing and low latency with no backlog.

## Extension Points

- Capture sources: DXGI/DXcam, OBS virtual source, browser tab capture, game hooks.
- Processing: edge sampling, palette clustering, dark-scene models, letterbox detection.
- Effects: beat detection, idle breathing, cinematic fades, profile-specific transforms.
- Backends: WLED, Hue, Nanoleaf, MQTT, vendor SDKs, local WebSocket clients.
- Profiles: automatic app matching, fullscreen detection, schedule-based switching.

# Feature Expansion Proposals

## Edge-Based Sampling

Samples only the outer bands of a monitor or window. Users want this because it feels closer to Ambilight and avoids UI elements in the center. Implement by slicing top/bottom/left/right strips from the captured frame, extracting one color per edge, and mapping edges to RGB zones. Use NumPy slicing and OpenCV resizing. Architecturally this belongs in `processing/edge_sampling.py` and should output a named palette, not only a single RGB.

## Cinematic Mode

Smooths transitions, detects letterbox bars, and lowers peak brightness during dark scenes. Users want movie lighting that feels immersive instead of twitchy. Implement with high smoothing, black-bar crop detection, percentile-based brightness, and scene-memory normalization. Use OpenCV for bar detection and NumPy percentiles.

## Adaptive Brightness Normalization

Prevents extremely bright scenes from blasting the keyboard and dark scenes from going fully dead. Implement a running luma model with attack/release curves. Keep it in `effects/adaptive_brightness.py` so it can be stacked after palette extraction.

## Smart Dark-Scene Handling

Detects whether a dark frame is intentional black, a fade, or just UI background. Users want dark scenes to remain atmospheric without flicker. Use mask pixel counts, rolling color confidence, and previous hue memory. If confidence is low, decay toward a dim previous color instead of pure black.

## Beat Detection

Adds music-reactive pulses. Users want RGB to respond to audio when visual content is static. Use `pycaw` for session peaks initially; advanced mode can use `sounddevice` plus `librosa` or simple FFT onset detection. Keep beat signals separate from color signals and combine in the effect pipeline.

## Music-Reactive Mode

Uses audio as the primary source when no visual target is active. Implement audio level, spectral centroid, and onset intensity mapping to brightness/saturation. Keep it optional because audio capture has permission and device complexity.

## Per-Zone Gradients

Maps multiple sampled regions to keyboard zones, LED strips, or OpenRGB zones. Users want richer lighting than a single color. Implement split palettes in `palette_extraction.py`, then add backend capability descriptors so dispatch knows whether zones, LEDs, or single-device color is supported.

## Monitor Edge Mapping

Lets users map physical devices to screen edges. Implement a `ZoneMap` model with named zones like `left`, `right`, `top`, `bottom`, `center`. Needed for WLED strips and multi-device setups.

## Fullscreen Auto-Switching

Detects fullscreen windows and switches profiles automatically. Use Win32 window rect vs monitor rect, process name matching, and foreground window events. Keep profile switching event-driven rather than checking every frame.

## Automatic Profile Switching

Maps process names to profiles: games use gaming, video players use movie, idle desktop uses calm. Implement in `profiles/profile_manager.py` with process/title match rules.

## RGB Effect Stacking

Allows ambient color plus brightness pulse plus idle fallback. Implement effects as pure functions or small stateful classes in `effects/effect_pipeline.py`. Effects should be ordered and inspect optional frame metadata.

## Idle Breathing Effects

Runs a subtle breathing animation when no target window or vivid pixels are available. Keep this in software until a backend is connected. Dispatch should still respect update throttling.

## Plugin API

Expose plugin interfaces for capture sources, processors, effects, and backends. Use Python entry points later:

```toml
[project.entry-points."lumisync.backends"]
wled = "lumisync_wled:WledBackend"
```

## WebSocket API

Broadcasts current color, FPS, backend status, and profile. Also accepts pause/profile commands. Use optional `websockets`; keep localhost-only by default.

## REST API

Useful for simple integrations and dashboards. Use FastAPI only as an optional extra because it increases dependency weight.

## MQTT Integration

Publishes colors and status to home automation. Use `paho-mqtt`. Keep payloads small and stable.

## WLED Integration

Controls LED strips over HTTP/UDP/WebSocket. Users want Ambilight strips. Implement as a backend with zone mapping and rate limiting.

## Philips Hue Support

Supports entertainment-area style lighting. Use Hue bridge APIs; this requires pairing flow and local network discovery. Keep separate from core.

## Nanoleaf Support

Controls panels or lines. Use local Nanoleaf API with token setup. Best implemented as a plugin backend.

## Discord Rich Presence

Shows active profile/backend and whether sync is running. Use `pypresence`. Must be opt-in.

## OBS Integration

Expose scene/profile changes to streamers. Start with WebSocket events; later integrate with `obs-websocket-py`.

## Stream Deck Integration

Use WebSocket/REST commands so Stream Deck plugins can toggle sync, switch profiles, or show backend status.

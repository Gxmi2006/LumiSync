# Migration Plan: KONSL Aura Sync to LumiSync

## Completed Repository Steps

- Public package introduced as `lumisync`.
- Legacy `konsl_aura_sync` module reduced to a compatibility shim.
- CLI changed to `python -m lumisync` and console script `lumisync`.
- PyInstaller build renamed to `LumiSync`.
- Backend detection remains centralized in `lumisync/backends/backend_manager.py`.
- Generic window detection replaces Spotify-only matching.
- Default config now targets the foreground window.
- Documentation repositioned around ambient RGB sync.

## Next Refactor Steps

1. Split `backend_manager.py` into a true manager plus separate OpenRGB-primary and legacy Aura implementation files.
2. Replace single `WindowFinder` with a `CaptureTargetResolver`.
3. Add capture mode dispatch: `active_window`, `window`, `monitor`, `region`.
4. Add monitor profile matching with MSS monitor indexes.
5. Introduce a `FrameSample` model carrying frame RGB, source metadata, and timing.
6. Introduce a `PaletteResult` model for single color, edge colors, zones, confidence, and mask stats.
7. Move effect application into `EffectPipeline` inside the main loop.
8. Add `BackendCapabilities` so each backend declares single-color, zone, LED, and gradient support.
9. Add a reconnect state machine with states: disabled, probing, connected, unavailable, retry_wait, fallback.
10. Add profile manager integration and process/title-based automatic switching.

## Replacing Spotify-Specific Logic

Old logic assumed a Spotify Chromium window. LumiSync should instead:

- target foreground window when no filters are configured
- allow process/title filters for games and browsers
- add fullscreen detection by comparing target rect to monitor rect
- add browser profile examples instead of hardcoded Spotify settings
- keep Spicetify/KONSL as just one possible user profile, not the project identity

## DXGI/Desktop Duplication Direction

MSS is simple and reliable, but DXGI/Desktop Duplication can reduce latency and improve fullscreen capture. Evaluate:

- `dxcam` for Python-friendly Desktop Duplication
- fallback to MSS when DXGI fails
- backend selection in `[performance].capture_backend`
- frame queue with latest-frame dropping

## Event-Driven Architecture

Long term, avoid doing every task every frame:

- backend probes run on timers/state transitions
- window detection runs at configurable intervals
- hotkeys enqueue commands
- config reload is an event
- frame loop only captures/processes/dispatches

## Profile Management

Profiles should be layered:

1. base config
2. named profile overrides
3. app/window match overrides
4. runtime hotkey overrides

This requires a merge system rather than mutating dataclasses directly.

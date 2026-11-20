# Changelog

All notable changes to LumiSync are documented here.

## Unreleased

### Added

- `--setup-check` command for first-time setup validation and human-friendly fix steps.
- Diagnostics now include OpenRGB device names, fallback state, selected capture target, capture region, and suggestions.
- Config validation with safe clamping for risky runtime values.
- Monitor and virtual-desktop region capture support in the runtime loop.
- Regression tests for visual priority, config validation, smoothing, and backend selection helpers.
- RGB fan support in OpenRGB device selection: fan hubs (cooler type) and motherboard ARGB headers are now picked up next to keyboards, and `fan`/`cooler` were added to the default `device_name_contains` list.
- README section on setting up RGB fans.
- `[performance]` config section is now honored: `adaptive_fps` drops to `idle_fps` after 3 seconds of an unchanging color, and `max_fps` caps the loop.

### Improved

- OpenRGB device-type matching now uses the enum name. Newer openrgb-python versions return a number from `str(device.type)`, so keyboards were never matched by type before.
- Visual Priority Engine now recognizes bright white and gray highlight rings, not only saturated colors.
- Scene harmony scoring now penalizes broad dark backgrounds more strongly.
- Setup and diagnostics commands avoid noisy console logging.
- Screen capture is shrunk straight from the capture buffer, so the full-resolution RGB copy is no longer made each frame.
- Region scoring ranks components by saliency first and fully scores only the strongest few, which cuts extraction time on busy frames by about a third.
- Palette histogram selection uses a partial sort and direct weighted means instead of full sorts and `numpy.average`.
- Debug-overlay payloads are only built while the overlay is enabled.
- The tray icon repaints at most twice a second and only for visible color changes.
- Uses `mss.MSS` when available to avoid the `mss.mss` deprecation warning on mss 10.

### Notes

- OpenRGB remains the primary hardware backend.
- Aura remains legacy opt-in.
- Multi-color gradients remain disabled by default; LumiSync outputs one best cinematic color.

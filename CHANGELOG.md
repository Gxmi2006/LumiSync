# Changelog

All notable changes to LumiSync are documented here.

## Unreleased

### Added

- `--setup-check` command for first-time setup validation and human-friendly fix steps.
- Diagnostics now include OpenRGB device names, fallback state, selected capture target, capture region, and suggestions.
- Config validation with safe clamping for risky runtime values.
- Monitor and virtual-desktop region capture support in the runtime loop.
- Regression tests for visual priority, config validation, smoothing, and backend selection helpers.

### Improved

- Visual Priority Engine now recognizes bright white and gray highlight rings, not only saturated colors.
- Scene harmony scoring now penalizes broad dark backgrounds more strongly.
- Setup and diagnostics commands avoid noisy console logging.

### Notes

- OpenRGB remains the primary hardware backend.
- Aura remains legacy opt-in.
- Multi-color gradients remain disabled by default; LumiSync outputs one best cinematic color.

# LumiSync

[![Windows 11](https://img.shields.io/badge/Windows-11-0A84FF?style=flat-square)](#requirements)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](#installation)
[![OpenRGB](https://img.shields.io/badge/OpenRGB-SDK%20Server%20Required-22C55E?style=flat-square)](#openrgb-setup)
[![Aura](https://img.shields.io/badge/ASUS-Aura%20%2F%20Armoury%20Crate-7C3AED?style=flat-square)](#asus-aura--armoury-crate)
[![License](https://img.shields.io/badge/License-MIT-111827?style=flat-square)](#license)

**Lightweight ambient RGB sync for Windows.**

LumiSync watches the colors in your games, movies, browser videos, anime, emulators, desktop windows, or monitors, then turns those colors into smooth RGB lighting for ASUS Aura / Armoury Crate devices or OpenRGB-compatible hardware.

It is built to feel like an open-source, laptop-friendly Ambilight engine: low overhead, clear diagnostics, easy configuration, and safe fallback behavior when RGB hardware is missing.

## What It Does

```text
game / movie / window / monitor
        -> capture a small frame region
        -> find visually important colors
        -> smooth transitions
        -> send RGB to Aura, OpenRGB, or software fallback
```

LumiSync is useful when you want:

- keyboard RGB that follows the mood of a game
- ambient color from YouTube, Netflix, anime, or local video
- OpenRGB-powered lighting without a heavy RGB suite
- ASUS laptop keyboard experiments without hard crashes when Aura exposes no devices
- a Python-based RGB engine you can inspect, tune, and extend

## Current Status

LumiSync is a real working Python desktop app, but it is still early-stage. The current runtime supports active-window and region-based capture, Aura/OpenRGB backends, software fallback, tray controls, hotkeys, debug overlays, smoothing, reconnect handling, and the Intelligent Visual Priority Engine.

Monitor sync and edge mapping are part of the architecture and config surface; the current production path is strongest for foreground/window/region sync.

Helpful docs:

- [Quick Start](docs/QUICKSTART.md)
- [RGB Backend Guide](docs/BACKENDS.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Architecture](docs/ARCHITECTURE.md)

## Screenshots And GIFs

Public demo assets should be added under `assets/`:

| Asset | What It Should Show |
| --- | --- |
| `assets/demo-game.gif` | A game scene changing color while keyboard RGB follows smoothly |
| `assets/demo-movie.gif` | Cinematic video/anime scene with subtle ambient transitions |
| `assets/visual-priority.gif` | Neon object selected over a dark background |
| `assets/debug-overlay.png` | Capture rectangle, FPS, backend, focal boxes, palette swatches |
| `assets/backend-report.png` | Aura/OpenRGB/software fallback diagnostics |

## RGB Backends

LumiSync uses a strict backend order:

1. **ASUS Aura / Armoury Crate** is attempted first.
2. **OpenRGB** is used as the fallback hardware backend.
3. **Software fallback** keeps the app running when no RGB backend works.

Software fallback is not an error. It means capture, processing, overlays, tray, hotkeys, and diagnostics still work, but no hardware color writes are attempted.

Example startup report:

```text
LumiSync backend status:
  Aura: no devices - Aura SDK is installed, but it reported no supported keyboard lighting devices
  OpenRGB: not running - OpenRGB SDK server probe ended with not running
  Active backend: software fallback
```

## OpenRGB Setup

**OpenRGB must have the SDK Server enabled.** Installing OpenRGB alone is not enough.

1. Install OpenRGB.
2. Open OpenRGB.
3. Open the **SDK Server** tab.
4. Click **Start Server**.
5. Keep the default server address unless you changed it:

```toml
[openrgb]
address = "127.0.0.1"
port = 6742
```

If OpenRGB is installed but the server is not running, LumiSync reports `OpenRGB: not running` or `OpenRGB: timeout` and continues in software fallback mode.

## ASUS Aura / Armoury Crate

LumiSync talks to Aura through the Windows COM ProgID:

```text
aura.sdk.1
```

On startup LumiSync:

1. loads `pywin32` COM support
2. creates the Aura SDK COM object
3. calls `SwitchMode()`
4. enumerates keyboard and notebook keyboard device types
5. reports whether Aura is available, missing, errored, or has no keyboard devices

Important ASUS laptop note: Armoury Crate can be installed while the public Aura SDK exposes **no controllable keyboard device**. LumiSync handles that safely as `Aura: no devices`, then tries OpenRGB or software fallback.

## Intelligent Visual Priority Engine

Naive average color often chooses muddy backgrounds. LumiSync includes an optional **Intelligent Visual Priority Engine** that looks for colors people actually notice:

- glowing regions
- saturated objects
- cinematic highlights
- high-contrast focal areas
- edge-rich visual objects
- center-biased subjects
- temporally stable regions

Example: if a frame has a dark blue background and a neon purple ring in the center, LumiSync should prioritize the purple ring instead of washing the keyboard dark blue.

Enable and tune it in:

```toml
[visual_priority]
enabled = true
glow_weight = 1.25
center_weight = 0.70
saliency_threshold = 0.34
debug_regions = true
debug_saliency_map = true
debug_palette = true
```

Use `--debug-overlay` to see focal boxes, region scores, saliency preview, and palette swatches.

## Features

- Active-window RGB sync
- Targeted window matching by process name or title
- Region capture using normalized crop ratios
- Monitor detection and monitor-capture scaffolding
- OpenCV + NumPy frame processing
- Intelligent Visual Priority Engine
- Dominant color and smart palette extraction
- Multi-region gradient colors for zone-capable devices
- Smooth interpolation with configurable strength
- Aura COM backend
- OpenRGB SDK backend
- Software fallback mode
- Tray menu
- Global hotkeys
- Debug overlay
- Startup shortcut integration
- Backend reconnect handling
- Diagnostics command
- PyInstaller packaging

## Requirements

- Windows 11
- Python 3.10+
- Optional for ASUS control: Armoury Crate / Aura components
- Optional for broad RGB hardware: OpenRGB with SDK Server enabled

## Installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Check that the CLI works:

```powershell
python -m lumisync --help
```

## Quick Start

1. Start OpenRGB SDK Server if you want OpenRGB hardware output.
2. Run LumiSync:

```powershell
python -m lumisync --config .\config.toml
```

3. Put a game, video, or browser window in focus.
4. Use the debug overlay while tuning:

```powershell
python -m lumisync --config .\config.toml --debug-overlay
```

5. Read the backend report printed at startup.

## Usage Examples

Sync the current foreground window:

```toml
[app]
capture_mode = "active_window"

[window]
process_name = ""
title_contains = ""
```

Sync a specific game:

```toml
[window]
process_name = "Game.exe"
title_contains = ""
```

Sync YouTube in Chrome:

```toml
[window]
process_name = "chrome.exe"
title_contains = "YouTube"
```

Sync only the middle of a video or emulator:

```toml
[capture]
left_ratio = 0.12
top_ratio = 0.08
width_ratio = 0.76
height_ratio = 0.82
```

Print diagnostics:

```powershell
python -m lumisync --diagnostics
```

Set a test color:

```powershell
python -m lumisync --test-color 22CCFF
```

## Hotkeys

| Hotkey | Action |
| --- | --- |
| `Ctrl+Alt+P` | Pause/resume sync |
| `Ctrl+Alt+R` | Reload config |
| `Ctrl+Alt+D` | Toggle debug overlay |
| `Ctrl+Alt+Q` | Quit |

The `keyboard` package may need administrator privileges on some Windows systems.

## FPS And Performance Tuning

LumiSync is designed for 10-30 FPS ambient updates.

| Use Case | Suggested FPS | Notes |
| --- | ---: | --- |
| Gaming | 24-30 | Lower smoothing for responsiveness |
| Movies/anime | 16-20 | Higher smoothing for cinematic fades |
| Battery laptop | 8-12 | Lower downscale resolution and update rate |
| Debug tuning | 10-20 | Overlay adds some UI overhead |

Useful settings:

```toml
[app]
fps = 20

[processing]
downscale_width = 160
downscale_height = 90

[smoothing]
strength = 0.62

[rgb]
minimum_update_interval_ms = 16
minimum_color_delta = 2.0
```

Lower FPS and downscale size reduce CPU usage. Higher smoothing reduces flicker. Higher color delta reduces hardware write frequency.

## Configuration

The main config is [config.toml](config.toml). Important sections:

- `[app]`: FPS, capture mode, backend preference
- `[window]`: target app matching
- `[capture]`: crop region
- `[processing]`: color filtering and downscale settings
- `[visual_priority]`: focal object scoring
- `[smoothing]`: transition behavior
- `[rgb]`: update throttling and reconnect timing
- `[aura]`: ASUS Aura device types
- `[openrgb]`: SDK Server connection
- `[diagnostics]`: backend probing behavior
- `[logging]`: log level and rotation

More detail: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

## Troubleshooting

### OpenRGB does not work

Make sure the SDK Server is running:

1. Open OpenRGB.
2. Go to **SDK Server**.
3. Click **Start Server**.
4. Run `python -m lumisync --diagnostics`.

### Aura says `no devices`

Armoury Crate is installed, but Aura did not expose a supported keyboard device. This is common on some ASUS laptops. LumiSync will try OpenRGB next, then software fallback.

### Active backend is `software fallback`

The app is healthy, but no hardware backend is currently usable. Capture, processing, overlays, and hotkeys still work.

### Colors look muddy

Keep `visual_priority.enabled = true`, raise `visual_priority.glow_weight`, lower `visual_priority.saliency_threshold`, or raise `processing.saturation_multiplier`.

### Colors flicker

Raise `smoothing.strength`, raise `rgb.minimum_color_delta`, or reduce `app.fps`.

### Wrong part of the screen is sampled

Run with `--debug-overlay` and tune `[window]` plus `[capture]`.

### CPU usage is too high

Lower `app.fps`, reduce `processing.downscale_width/downscale_height`, or use a smaller capture region.

Logs are written to:

```text
%APPDATA%\LumiSync\logs\lumisync.log
```

## Build

```powershell
.\build.ps1
```

Output:

```text
dist\LumiSync\LumiSync.exe
```

Run:

```powershell
.\dist\LumiSync\LumiSync.exe --config .\config.toml
```

## Architecture

```text
lumisync/
  core/         app loop, config, color, smoothing, logging
  capture/      window, region, and monitor capture
  processing/   saliency, visual priority, palette extraction
  backends/     Aura, OpenRGB, software fallback
  effects/      adaptive brightness and effect pipeline
  ui/           tray and hotkeys
  overlays/     debug overlay
  diagnostics/  backend/runtime reports
  profiles/     profile loading
  utils/        Windows startup helpers
```

The backend manager is the only layer that talks to RGB SDKs. The capture and processing pipeline keeps running even if every RGB backend fails.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Roadmap

- Full monitor sync runtime mode
- Edge sampling and Ambilight-style zone mapping
- DXcam/Desktop Duplication capture backend
- Automatic fullscreen detection
- Automatic profile switching by app/game
- WLED backend
- Philips Hue and Nanoleaf integrations
- WebSocket/REST API
- OBS and Stream Deck integrations
- GUI profile editor
- Signed Windows builds

## Contributing

LumiSync is designed to be contributor-friendly. Good areas to help:

- test Aura/OpenRGB behavior on specific hardware
- improve visual-priority scoring profiles
- add capture backends
- add RGB backends
- improve debug overlays
- write docs for common hardware setups
- create screenshots and demo GIFs

See [docs/GITHUB_ECOSYSTEM.md](docs/GITHUB_ECOSYSTEM.md) for labels, issue templates, release naming, and project presentation ideas.

## License

MIT License. See [LICENSE](LICENSE).

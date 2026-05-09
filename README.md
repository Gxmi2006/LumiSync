# LumiSync

[![Windows 11](https://img.shields.io/badge/Windows-11-0A84FF?style=flat-square)](#requirements)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](#quick-start)
[![OpenRGB](https://img.shields.io/badge/OpenRGB-SDK%20Server%20Required-22C55E?style=flat-square)](#openrgb-setup)
[![PyInstaller](https://img.shields.io/badge/Build-PyInstaller-111827?style=flat-square)](#build)
[![License](https://img.shields.io/badge/License-MIT-111827?style=flat-square)](#license)

**Lightweight OpenRGB ambient lighting for Windows.**

LumiSync watches the colors in your games, movies, browser videos, anime, emulators, desktop windows, and monitors, then turns them into smooth OpenRGB lighting with cinematic color selection and low overhead.

It is built for people who want ambient RGB without a heavy vendor suite: transparent diagnostics, simple TOML config, smart single-color extraction, and safe software fallback when RGB hardware is unavailable.

```text
game / movie / browser / window
        -> capture a small region
        -> find focal objects or scene harmony colors
        -> smooth and style the palette
        -> send one best color to OpenRGB or software fallback
```

## Why LumiSync

| What you want | How LumiSync helps |
| --- | --- |
| RGB that follows games and videos | Captures the active window or a tuned region in real time |
| Better colors than average sampling | Prioritizes glowing objects, vivid highlights, and pleasing scene palettes |
| Elegant keyboard color | Sends one best cinematic scene color instead of flashy gradients |
| Works across laptops and desktops | Uses OpenRGB as the default hardware path |
| No crashes when hardware is missing | Falls back to software mode while capture and overlays keep running |
| Easy tuning | Uses `config.toml`, diagnostics, hotkeys, and debug overlays |

## Requirements

- Windows 11
- Python 3.10+ for source installs
- OpenRGB for hardware output
- OpenRGB SDK Server enabled
- Optional: PyInstaller for standalone executable builds

## Quick Start

### 1. Install OpenRGB

Download OpenRGB from [openrgb.org](https://openrgb.org/).

**Important:** OpenRGB must have the SDK Server running.

1. Open OpenRGB.
2. Open the **SDK Server** tab.
3. Click **Start Server**.
4. Keep the default port unless you changed it:

```toml
[openrgb]
address = "127.0.0.1"
port = 6742
```

### 2. Install LumiSync

```powershell
git clone https://github.com/Gxmi2006/LumiSync.git
cd LumiSync
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Run

```powershell
python -m lumisync --config .\config.toml
```

To see what LumiSync detected:

```powershell
python -m lumisync --diagnostics
```

Expected backend behavior:

```text
Aura: disabled - Skipped because app.controller is 'openrgb'
OpenRGB: connected - ready for hardware RGB updates
Active backend: openrgb
```

If OpenRGB is not running, LumiSync enters **software fallback**. That is safe: capture, smart color extraction, tray controls, hotkeys, and the debug overlay still work, but no hardware writes are sent.

## Screenshots And GIFs

Public demo assets should be added under `assets/`.

| Asset | What it should show |
| --- | --- |
| `assets/demo-game.gif` | A game scene changing while OpenRGB keyboard colors follow smoothly |
| `assets/demo-movie.gif` | Film/anime lighting with subtle cinematic transitions |
| `assets/visual-priority.gif` | Neon object selected over a dark background |
| `assets/scene-harmony.gif` | No single object, but LumiSync picks an elegant scene palette |
| `assets/debug-overlay.png` | Capture rectangle, FPS, backend, focal boxes, palette swatches |
| `assets/openrgb-setup.png` | OpenRGB SDK Server tab with Start Server enabled |

## Features

| Area | Capabilities |
| --- | --- |
| Capture | Active-window sync, process/title targeting, normalized region capture, monitor detection |
| Color engine | Saliency detection, focal region scoring, smart scene-harmony fallback, OpenCV/NumPy palette extraction |
| Single-color output | One best cinematic scene color by default |
| Smoothing | Low-flicker interpolation, update throttling, configurable FPS |
| OpenRGB | SDK Server connection, reconnect handling, all-device fallback when no keyboard match exists |
| Desktop app | Tray icon, global hotkeys, debug overlay, startup shortcut support |
| Reliability | Software fallback mode, structured diagnostics, rotating logs |
| Packaging | PyInstaller build for a standalone Windows executable |

## Smart Color Engine

LumiSync does not just average the screen.

### Focal Mode

When a scene has an obvious visual subject, LumiSync prioritizes it:

- neon rings and glow effects
- saturated foreground objects
- cinematic highlights
- high-contrast edges
- centered visual subjects
- temporally stable regions

Example: a dark scene with a purple glowing ring should output purple, not muddy dark blue.

### Scene Harmony Mode

When there is no single appealing object, LumiSync switches to scene harmony:

- filters near-black, gray, and dull pixels
- groups colors into stable HSV families
- scores them by vividness, coverage, brightness, contrast, and elegance
- chooses the best matching scene color instead of a raw average
- returns a small palette for multi-zone output

```toml
[palette]
fallback_mode = "scene_harmony"
multi_color_mode = "cinematic"
minimum_focal_confidence = 0.35
palette_size = 1
harmony_strength = 0.35
```

Palette modes:

| Mode | Result |
| --- | --- |
| `scene` | Uses colors sampled from the current frame |
| `harmonic` | Generates elegant analogous colors around the selected hue |
| `cinematic` | Default. Uses restrained lower-brightness palette styling |

## OpenRGB Setup

OpenRGB is the default hardware backend. It works with many keyboards, mice, motherboards, RAM kits, LED strips, and laptop RGB devices supported by OpenRGB.

1. Install OpenRGB.
2. Start OpenRGB.
3. Open **SDK Server**.
4. Click **Start Server**.
5. Run:

```powershell
python -m lumisync --diagnostics
```

Useful statuses:

| Status | Meaning |
| --- | --- |
| `connected` | LumiSync can send colors through OpenRGB |
| `not running` | OpenRGB SDK Server is not listening |
| `timeout` | SDK Server did not respond fast enough |
| `no devices` | OpenRGB connected but exposed no usable devices |
| `not found` | Python OpenRGB dependency is missing |

By default, LumiSync prefers keyboard/laptop-like devices, then falls back to all OpenRGB devices so desktops and non-keyboard setups still work.

## ASUS Aura Note

Aura / Armoury Crate support remains in the codebase as an advanced legacy backend, but it is disabled by default because laptop Aura SDK device exposure is inconsistent.

To experiment with Aura manually:

```toml
[app]
controller = "aura"

[aura]
enabled = true
```

Most users should use OpenRGB.

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
```

Sync YouTube in Chrome:

```toml
[window]
process_name = "chrome.exe"
title_contains = "YouTube"
```

Sample only the center of a video or emulator:

```toml
[capture]
left_ratio = 0.12
top_ratio = 0.08
width_ratio = 0.76
height_ratio = 0.82
```

Show the debug overlay:

```powershell
python -m lumisync --config .\config.toml --debug-overlay
```

Send a test color:

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

The `keyboard` package may require administrator privileges on some Windows systems.

## Performance Tuning

LumiSync is designed for 10-30 FPS ambient updates.

| Use case | FPS | Suggested feel |
| --- | ---: | --- |
| Gaming | 24-30 | Responsive |
| Movies/anime | 16-20 | Smooth and cinematic |
| Battery laptop | 8-12 | Low overhead |
| Debug tuning | 10-20 | Overlay-friendly |

Key settings:

```toml
[app]
fps = 20

[processing]
downscale_width = 160
downscale_height = 90

[smoothing]
strength = 0.76

[rgb]
minimum_update_interval_ms = 16
minimum_color_delta = 2.0
```

Lower FPS and downscale size reduce CPU usage. Higher smoothing reduces flicker. Higher color delta reduces hardware write frequency.

## Configuration

The main config is [config.toml](config.toml).

| Section | Controls |
| --- | --- |
| `[app]` | FPS, capture mode, backend preference |
| `[openrgb]` | SDK Server host, port, timeouts, device fallback |
| `[palette]` | Scene harmony and single-color palette style |
| `[visual_priority]` | Focal object detection and region scoring |
| `[gradient]` | Optional multi-region output, disabled by default |
| `[window]` | Target process/title matching |
| `[capture]` | Region crop ratios and offsets |
| `[processing]` | Downscale, thresholds, color adjustments |
| `[smoothing]` | Color transition behavior |
| `[rgb]` | Update throttling and reconnect timing |

More detail: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

## Troubleshooting

### OpenRGB does not connect

Open OpenRGB, go to **SDK Server**, click **Start Server**, then run:

```powershell
python -m lumisync --diagnostics
```

### Active backend is `software fallback`

LumiSync is healthy, but no hardware backend is usable. Start OpenRGB SDK Server or check whether OpenRGB detects your hardware.

### Colors look muddy

Keep scene harmony enabled and raise saturation slightly:

```toml
[palette]
fallback_mode = "scene_harmony"

[processing]
saturation_multiplier = 1.05
brightness_multiplier = 0.78
```

### A bright object is being missed

Lower the focal threshold:

```toml
[visual_priority]
saliency_threshold = 0.28

[palette]
minimum_focal_confidence = 0.30
```

### Colors flicker

```toml
[smoothing]
strength = 0.72

[rgb]
minimum_color_delta = 4.0
```

### Wrong screen area is sampled

Run with `--debug-overlay`, then tune `[window]` and `[capture]`.

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

Run the packaged app:

```powershell
.\dist\LumiSync\LumiSync.exe --diagnostics
```

## Architecture

```text
lumisync/
  core/         app loop, config, color, smoothing, logging
  capture/      window, region, and monitor capture
  processing/   saliency, visual priority, scene harmony, palette extraction
  backends/     OpenRGB primary, Aura legacy, software fallback
  effects/      adaptive brightness and audio pulse hooks
  ui/           tray and hotkeys
  overlays/     debug overlay
  diagnostics/  backend/runtime reports
  profiles/     profile loading
  utils/        Windows startup helpers
```

The backend manager is the only layer that talks to RGB SDKs. Capture and color processing continue even if OpenRGB is unavailable.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Roadmap

- Full monitor sync runtime mode
- Edge sampling and Ambilight-style zone mapping
- DXcam/Desktop Duplication capture backend
- Automatic fullscreen detection and profile switching
- WLED, Philips Hue, and Nanoleaf backends
- WebSocket/REST API
- OBS and Stream Deck integrations
- GUI profile editor
- Signed Windows builds

## Contributing

Good areas to help:

- test OpenRGB behavior on real hardware
- improve scene harmony and visual-priority scoring
- add capture backends
- improve zone mapping for keyboards and LED strips
- create screenshots and demo GIFs
- write hardware-specific setup guides

See [docs/GITHUB_ECOSYSTEM.md](docs/GITHUB_ECOSYSTEM.md) for labels, issue templates, release naming, and project presentation ideas.

## License

MIT License. See [LICENSE](LICENSE).

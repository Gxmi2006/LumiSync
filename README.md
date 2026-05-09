# LumiSync

[![Windows 11](https://img.shields.io/badge/Windows-11-0A84FF?style=flat-square)](#requirements)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](#installation)
[![OpenRGB](https://img.shields.io/badge/OpenRGB-SDK%20Server%20Required-22C55E?style=flat-square)](#openrgb-setup)
[![Aura](https://img.shields.io/badge/ASUS-Aura%20%2F%20Armoury%20Crate-7C3AED?style=flat-square)](#asus-aura--armoury-crate)
[![License](https://img.shields.io/badge/License-MIT-111827?style=flat-square)](LICENSE)

**Lightweight ambient RGB sync for Windows.**

LumiSync watches the colors in your games, movies, browser videos, anime, and desktop windows, then drives smooth RGB lighting on ASUS Aura / Armoury Crate devices or any OpenRGB-compatible hardware — with no crashes if no RGB hardware is found.

> Think open-source Ambilight for your keyboard: low overhead, clear diagnostics, easy config, and safe fallback behavior.

```
game / movie / window / monitor
        ↓ capture a small frame region
        ↓ find visually important colors
        ↓ smooth transitions
        ↓ send RGB to Aura, OpenRGB, or software fallback
```

---

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [RGB Backend Setup](#rgb-backend-setup)
- [Usage Examples](#usage-examples)
- [Intelligent Visual Priority Engine](#intelligent-visual-priority-engine)
- [Hotkeys](#hotkeys)
- [Performance Tuning](#fps-and-performance-tuning)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Build](#build)
- [Architecture](#architecture)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Quick Start

> Get running in under 5 minutes.

**1. Clone the repo**
```powershell
git clone https://github.com/Gxmi2006/LumiSync.git
cd LumiSync
```

**2. Create and activate a virtual environment**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **Activation blocked?** If you see `running scripts is disabled on this system`, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Type `Y`, then re-run the `Activate.ps1` line. You should see `(.venv)` appear at the start of your prompt.

**3. Install dependencies**
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**4. Run**
```powershell
python -m lumisync --config .\config.toml
```

On startup, LumiSync prints a backend report so you know exactly what connected:
```
LumiSync backend status:
  Aura: available
  OpenRGB: not running
  Active backend: Aura
```

If it shows `software fallback`, your capture pipeline is still fully running — just no RGB hardware was detected. See [RGB Backend Setup](#rgb-backend-setup).

---

## Current Status

LumiSync is a real working Python desktop app, but it is early-stage. The current runtime fully supports:

- Active-window and region-based capture
- Aura and OpenRGB backends with software fallback
- Tray controls, hotkeys, debug overlays
- Smoothing and reconnect handling
- Intelligent Visual Priority Engine

Monitor sync and edge mapping are designed into the architecture; the strongest production path today is foreground/window/region sync.

Helpful docs: [Quick Start](docs/QUICKSTART.md) · [Backend Guide](docs/BACKENDS.md) · [Configuration](docs/CONFIGURATION.md) · [Architecture](docs/ARCHITECTURE.md)

---

## Screenshots and GIFs

> Demo assets should be added under `assets/` before a public launch.

| Asset | What It Should Show |
|---|---|
| `assets/demo-game.gif` | Game scene changing color while keyboard RGB follows smoothly |
| `assets/demo-movie.gif` | Cinematic/anime scene with ambient transitions |
| `assets/visual-priority.gif` | Neon object selected over a dark background |
| `assets/debug-overlay.png` | Capture rectangle, FPS, backend, focal boxes, palette swatches |
| `assets/backend-report.png` | Aura / OpenRGB / software fallback diagnostics at startup |

---

## Requirements

- Windows 11
- Python 3.10+ (3.11 recommended)
- Optional: Armoury Crate / Aura components for ASUS keyboard control
- Optional: OpenRGB with **SDK Server enabled** for broader hardware support

Python packages are installed automatically from `requirements.txt` and include `pywin32`, `psutil`, `mss`, `numpy`, `opencv-python`, `pillow`, `openrgb-python`, `pystray`, `keyboard`, and `pycaw` (optional, for audio-reactive brightness).

---

## Installation

### Step 1 — Install Python

Download Python 3.11 from [python.org](https://www.python.org/downloads/). During setup, check **"Add Python to PATH"**.

Verify it installed correctly:
```powershell
py --version
```

### Step 2 — Get LumiSync

Clone with Git:
```powershell
git clone https://github.com/Gxmi2006/LumiSync.git
cd LumiSync
```

Or download the ZIP from GitHub and extract it, then open PowerShell inside the folder.

### Step 3 — Create a Virtual Environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

You must activate the environment **every time you open a new terminal**. The `(.venv)` prefix in your prompt confirms it is active.

### Step 4 — Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5 — Verify

```powershell
python -m lumisync --help
```

### Step 6 — Run

```powershell
python -m lumisync --config .\config.toml
```

> **Note:** The LF/CRLF warnings shown by `git add` are harmless — they are a Windows line-ending notice, not errors.

---

## RGB Backend Setup

LumiSync tries backends in this order: **Aura → OpenRGB → Software fallback**

### ASUS Aura / Armoury Crate

No extra setup needed if Armoury Crate is installed. LumiSync detects it automatically via the COM ProgID `aura.sdk.1` and calls `SwitchMode()` on your keyboard device.

> **Getting `Aura: no devices`?** This is common on ASUS laptops — Armoury Crate can be installed while the public Aura SDK exposes no controllable keyboard device. LumiSync handles this safely and moves on to OpenRGB or software fallback.

### OpenRGB

Installing OpenRGB alone is not enough — **the SDK Server must be running.**

1. Download and open [OpenRGB](https://openrgb.org/)
2. Go to the **SDK Server** tab
3. Click **Start Server**
4. Leave the defaults unless you changed them:

```toml
[openrgb]
address = "127.0.0.1"
port = 6742
```

### Software Fallback

Software fallback is not an error. It means:

- Capture, color extraction, and processing still run
- Debug overlay, tray icon, and hotkeys still work
- No RGB writes are attempted

This lets you tune and develop without needing any RGB hardware connected.

---

## Usage Examples

**Sync the current foreground window (default)**
```toml
[app]
capture_mode = "active_window"
```

**Sync a specific game**
```toml
[window]
process_name = "Game.exe"
```

**Sync YouTube in Chrome**
```toml
[window]
process_name = "chrome.exe"
title_contains = "YouTube"
```

**Sync only the center of a video or emulator**
```toml
[capture]
left_ratio   = 0.12
top_ratio    = 0.08
width_ratio  = 0.76
height_ratio = 0.82
```

**Debug overlay** — shows capture rectangle, FPS, backend, palette swatches
```powershell
python -m lumisync --config .\config.toml --debug-overlay
```

**List all visible windows**
```powershell
python -m lumisync --list-windows
```

**Print a full diagnostics report**
```powershell
python -m lumisync --diagnostics
```

**Test a specific color on your hardware**
```powershell
python -m lumisync --test-color 22CCFF
```

---

## Intelligent Visual Priority Engine

Naive average color often returns muddy backgrounds. The **Intelligent Visual Priority Engine** scores regions by what the eye actually notices:

- Glowing and emissive regions
- Saturated foreground objects
- Cinematic highlights
- High-contrast focal areas
- Edge-rich visual detail
- Center-biased subjects
- Temporally stable regions

**Example:** a frame with a dark blue background and a neon purple ring in the center will output purple, not dark blue.

Enable and tune it in `config.toml`:

```toml
[visual_priority]
enabled              = true
glow_weight          = 1.25
center_weight        = 0.70
saliency_threshold   = 0.34
debug_regions        = true
debug_saliency_map   = true
debug_palette        = true
```

Run with `--debug-overlay` to see focal boxes, region scores, saliency preview, and palette swatches live.

---

## Hotkeys

| Hotkey | Action |
|---|---|
| `Ctrl+Alt+P` | Pause / resume sync |
| `Ctrl+Alt+R` | Reload config |
| `Ctrl+Alt+D` | Toggle debug overlay |
| `Ctrl+Alt+Q` | Quit |

> The `keyboard` package may need administrator privileges on some Windows systems.

---

## FPS and Performance Tuning

LumiSync is designed for 10–30 FPS ambient updates.

| Use Case | FPS | Notes |
|---|:---:|---|
| Gaming | 24–30 | Lower smoothing for responsiveness |
| Movies / anime | 16–20 | Higher smoothing for cinematic fades |
| Battery laptop | 8–12 | Reduce downscale resolution too |
| Debug tuning | 10–20 | Overlay adds some UI overhead |

Key settings:
```toml
[app]
fps = 20

[processing]
downscale_width  = 160
downscale_height = 90

[smoothing]
strength = 0.62

[rgb]
minimum_update_interval_ms = 16
minimum_color_delta        = 2.0
```

Lower FPS and downscale size reduce CPU usage. Higher smoothing reduces flicker. Higher `minimum_color_delta` reduces how often RGB writes go to hardware.

---

## Configuration

The main config is [`config.toml`](config.toml). Key sections:

| Section | Controls |
|---|---|
| `[app]` | FPS, capture mode, backend preference |
| `[window]` | Target app matching by process name or title |
| `[capture]` | Crop region ratios |
| `[processing]` | Color filtering and downscale resolution |
| `[visual_priority]` | Focal object scoring weights |
| `[smoothing]` | Transition speed and interpolation |
| `[rgb]` | Update throttling and reconnect timing |
| `[aura]` | ASUS Aura device types |
| `[openrgb]` | SDK Server address and port |
| `[diagnostics]` | Backend probing behavior |
| `[logging]` | Log level and rotation |

Full reference: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

---

## Troubleshooting

**OpenRGB does not work**
Make sure the SDK Server is running: open OpenRGB → SDK Server tab → Start Server. Then run `python -m lumisync --diagnostics`.

**Aura says `no devices`**
Your laptop may not expose the keyboard through the public Aura SDK. LumiSync will use OpenRGB or software fallback automatically.

**Active backend is `software fallback`**
The app is healthy — no hardware backend is currently connected. Capture, overlays, and hotkeys still work fully.

**Colors look muddy**
Keep `visual_priority.enabled = true`, raise `glow_weight`, lower `saliency_threshold`, or raise `processing.saturation_multiplier`.

**Colors flicker**
Raise `smoothing.strength`, raise `rgb.minimum_color_delta`, or lower `app.fps`.

**Wrong part of the screen is sampled**
Run with `--debug-overlay` and tune `[window]` and `[capture]` settings.

**CPU usage is too high**
Lower `app.fps`, reduce `processing.downscale_width/downscale_height`, or narrow the capture region.

**`running scripts is disabled on this system`**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Logs are written to `%APPDATA%\LumiSync\logs\lumisync.log`.

---

## Build

```powershell
.\build.ps1
```

Output:
```
dist\LumiSync\LumiSync.exe
```

Run the standalone executable:
```powershell
.\dist\LumiSync\LumiSync.exe --config .\config.toml
```

---

## Architecture

```
lumisync/
  core/         app loop, config, color, smoothing, logging
  capture/      window, region, and monitor capture
  processing/   saliency, visual priority, palette extraction
  backends/     Aura, OpenRGB, software fallback
  effects/      adaptive brightness and effect pipeline
  ui/           tray and hotkeys
  overlays/     debug overlay
  diagnostics/  backend and runtime reports
  profiles/     profile loading
  utils/        Windows startup helpers
```

The backend manager is the only layer that touches RGB SDKs. The capture and processing pipeline keeps running even if every RGB backend fails.

Full details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Roadmap

- Full monitor sync runtime mode
- Edge sampling and Ambilight-style zone mapping
- DXcam / Desktop Duplication capture backend
- Automatic fullscreen detection and profile switching
- WLED, Philips Hue, and Nanoleaf backends
- WebSocket / REST API
- OBS and Stream Deck integrations
- GUI profile editor
- Signed Windows builds

See [docs/FEATURE_EXPANSION.md](docs/FEATURE_EXPANSION.md) and [docs/VISION.md](docs/VISION.md).

---

## Contributing

LumiSync is built to be easy to extend. Good areas to help:

- Test Aura / OpenRGB behavior on specific hardware
- Improve visual-priority scoring for different content types
- Add capture or RGB backends
- Improve debug overlays
- Write hardware-specific setup guides
- Record demo GIFs and screenshots

See [docs/GITHUB_ECOSYSTEM.md](docs/GITHUB_ECOSYSTEM.md) for issue templates, labels, and release strategy.

---

## License

MIT License. See [LICENSE](LICENSE).

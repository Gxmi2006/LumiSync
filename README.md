# LumiSync

[![Windows](https://img.shields.io/badge/platform-Windows%2011-0A84FF?style=flat-square)](#requirements)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)](https://www.python.org/)
[![RGB](https://img.shields.io/badge/RGB-Aura%20%7C%20OpenRGB-7C3AED?style=flat-square)](#rgb-backend-setup)
[![License](https://img.shields.io/badge/license-MIT-111827?style=flat-square)](LICENSE)

**A lightweight open-source ambient RGB synchronization engine for Windows.**

LumiSync samples colors from games, movies, browsers, streaming apps, and desktop windows, then translates them into smooth, low-latency RGB lighting for ASUS Aura and OpenRGB devices.

> Similar in spirit to Ambilight, LIGHTSYNC, Razer Ambient Awareness, Hyperion, and SignalRGB — but smaller, open-source, Python-hackable, and laptop-friendly.

---

## Quick Start

> Get up and running in under 5 minutes.

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

> If you see `running scripts is disabled on this system`, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then re-run the `Activate.ps1` line. You should see `(.venv)` appear at the start of your prompt.

**3. Install dependencies**
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**4. Run LumiSync**
```powershell
python -m lumisync --config .\config.toml
```

That's it. LumiSync will start, detect your RGB hardware, and begin syncing.

---

## Highlights

- Sync RGB from the foreground window, a named app, a custom region, or a monitor
- Extract dominant colors with OpenCV + NumPy while filtering dark UI noise
- Smooth color transitions to avoid flicker and harsh jumps
- Supports ASUS Aura / Armoury Crate COM and OpenRGB SDK
- Continues running in software fallback mode when no RGB hardware is present
- Tray icon, global hotkeys, debug overlay, startup shortcut, and auto-reconnect

---

## Requirements

**System**
- Windows 11
- Python 3.10 or newer (3.11 recommended)
- Optional: Armoury Crate / Aura components for ASUS Aura control
- Optional: OpenRGB with SDK server enabled

**Python packages** (installed automatically via `requirements.txt`)
- `pywin32`, `psutil`, `mss`
- `numpy`, `opencv-python`, `pillow`
- `openrgb-python`
- `pystray`, `keyboard`
- `pycaw` *(optional — needed for audio-reactive brightness)*

---

## Installation (Detailed)

### Step 1 — Install Python

Download Python 3.11 from [python.org](https://www.python.org/downloads/).

During installation, make sure to check **"Add Python to PATH"**.

Verify it works:
```powershell
py --version
```

### Step 2 — Download LumiSync

Either clone with Git:
```powershell
git clone https://github.com/Gxmi2006/LumiSync.git
cd LumiSync
```

Or download the ZIP from GitHub and extract it, then open PowerShell inside the folder.

### Step 3 — Create a Virtual Environment

A virtual environment keeps LumiSync's packages separate from your system Python.

```powershell
py -3.11 -m venv .venv
```

Activate it:
```powershell
.\.venv\Scripts\Activate.ps1
```

You should now see `(.venv)` at the start of your terminal line. **You must activate the environment every time you open a new terminal.**

> **Activation error?** If PowerShell blocks the script, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Type `Y` when prompted, then activate again.

### Step 4 — Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This installs everything LumiSync needs. It may take a minute or two.

### Step 5 — Configure

Open `config.toml` in any text editor. The default config works out of the box. Common things to change:

```toml
[app]
capture_mode = "active_window"   # what to sync from

[window]
process_name = "chrome.exe"      # sync a specific app (leave blank for foreground)
title_contains = "YouTube"       # narrow by window title
```

Full config reference: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

### Step 6 — Run

```powershell
python -m lumisync --config .\config.toml
```

On startup, LumiSync prints a backend status report:

```
LumiSync backend status:
  Aura: available
  OpenRGB: not running
  Active backend: Aura
```

If it says `software fallback`, your capture pipeline is healthy but no RGB hardware was detected. See [RGB Backend Setup](#rgb-backend-setup) below.

---

## Usage

**Sync the foreground app (default)**
```toml
[app]
capture_mode = "active_window"
```

**Sync a specific game or app**
```toml
[window]
process_name = "Game.exe"
```

**Sync a browser video (e.g. YouTube on Chrome)**
```toml
[window]
process_name = "chrome.exe"
title_contains = "YouTube"
```

**Sync a specific region of the screen**
```toml
[capture]
left_ratio   = 0.12
top_ratio    = 0.08
width_ratio  = 0.76
height_ratio = 0.82
```

**Debug overlay** — shows capture rectangle, detected color, FPS, and backend state
```powershell
python -m lumisync --config .\config.toml --debug-overlay
```

**List all visible windows**
```powershell
python -m lumisync --list-windows
```

**Test a specific color on your hardware**
```powershell
python -m lumisync --test-color 22CCFF
```

---

## RGB Backend Setup

### ASUS Aura / Armoury Crate

LumiSync uses the Aura COM ProgID `aura.sdk.1`. No extra setup is needed if Armoury Crate is installed — LumiSync detects it automatically on startup.

> **Getting `Aura: no devices`?** Many ASUS laptops have Armoury Crate installed but do not expose the keyboard through the public Aura SDK. This is normal. Use OpenRGB or software fallback mode instead.

### OpenRGB

1. Download and open [OpenRGB](https://openrgb.org/)
2. Go to the **SDK Server** tab
3. Click **Start Server** (or launch OpenRGB with `--server`)
4. Leave the default address `127.0.0.1` and port `6742` unless you changed them

LumiSync will automatically connect to OpenRGB on startup.

### Software Fallback

If neither Aura nor OpenRGB is available, LumiSync runs in software fallback mode. This means:

- Capture and color extraction still run normally
- Debug overlay, tray icon, and hotkeys still work
- No RGB writes are attempted

This is intentional — the app won't crash just because no hardware is found.

---

## Hotkeys

| Hotkey | Action |
|---|---|
| `Ctrl+Alt+P` | Pause / resume sync |
| `Ctrl+Alt+R` | Reload config |
| `Ctrl+Alt+D` | Toggle debug overlay |
| `Ctrl+Alt+Q` | Quit |

> On some Windows systems, the `keyboard` package requires administrator privileges.

---

## Configuration

The `config.toml` file is fully commented. Key settings:

| Setting | What it does |
|---|---|
| `app.fps` | Lower to reduce CPU and battery usage |
| `smoothing.strength` | Higher = slower transitions; lower = snappier |
| `processing.black_threshold` | Raise to ignore dark UI backgrounds |
| `processing.saturation_multiplier` | Raise for more vivid colors |
| `processing.downscale_width/height` | Lower for less CPU usage |

**Recommended presets:**

| Mode | FPS | Smoothing | Downscale |
|---|---|---|---|
| Gaming | 30 | 0.40–0.50 | 160×90 |
| Movies / anime | 16–20 | 0.70–0.85 | 160×90 |
| Battery saver | 10 | 0.60 | 96×54 |

Full documentation: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

---

## Architecture

```
lumisync/
  core/          app loop, config, color, smoothing, logging, websocket API
  capture/       window detection, monitor detection, region and monitor capture
  processing/    palette extraction and frame reduction
  backends/      Aura / OpenRGB / software fallback backend manager
  effects/       adaptive brightness, audio-reactive hooks, effect pipeline
  ui/            tray icon and hotkeys
  overlays/      debug overlay
  diagnostics/   startup status and environment reports
  profiles/      profile manager
  presets/       future built-in profile catalog
  utils/         Windows startup helpers
```

Runtime flow:
```
target selection → capture → downscale → pixel filtering → palette extraction
→ smoothing / effects → backend manager → Aura / OpenRGB / software fallback
```

The backend manager is the only place that touches RGB SDKs. Aura and OpenRGB can fail or time out without affecting capture, processing, tray, overlay, or hotkeys.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full details.

---

## Build (Standalone Executable)

```powershell
.\build.ps1
```

Output:
```
dist\LumiSync\LumiSync.exe
```

Run:
```powershell
.\dist\LumiSync\LumiSync.exe --config .\config.toml
```

---

## Troubleshooting

**Colors flicker**
Raise `smoothing.strength`, raise `rgb.minimum_color_delta`, or lower `app.fps`.

**Colors are too dark**
Lower `processing.black_threshold` or raise `processing.brightness_multiplier`.

**Wrong content is being sampled**
Enable the debug overlay and tune `[window]` and `[capture]` ratios.

**CPU usage is too high**
Lower FPS, reduce downscale resolution, or narrow the capture region.

**OpenRGB says `not running` or `timeout`**
Start the OpenRGB SDK server and confirm it's on `127.0.0.1:6742`.

**Aura says `no devices`**
Your laptop may not expose the keyboard through the public Aura SDK. Try OpenRGB instead.

**No color changes but app is running**
Check the startup backend report. If active backend is `software fallback`, no hardware backend connected.

**`running scripts is disabled on this system`**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Roadmap

- Monitor edge mapping and Ambilight-style multi-zone output
- DXcam / Desktop Duplication capture backend
- Automatic fullscreen detection and profile switching
- WLED, Philips Hue, Nanoleaf, MQTT, and WebSocket integrations
- Plugin API for capture sources, effects, and RGB backends
- OBS and Stream Deck integrations for creators
- Profile editor UI and signed Windows builds

See [docs/FEATURE_EXPANSION.md](docs/FEATURE_EXPANSION.md) and [docs/VISION.md](docs/VISION.md).

---

## Contributing

LumiSync is intentionally modular. Good first contribution areas:

- Add new capture targets
- Improve device detection
- Add OpenRGB device mappings
- Tune processing profiles
- Record demo GIFs and screenshots
- Write backend diagnostics
- Improve docs for specific hardware models

Read [docs/GITHUB_ECOSYSTEM.md](docs/GITHUB_ECOSYSTEM.md) for issue templates, labels, and release strategy.

---

## License

MIT License. See [LICENSE](LICENSE).

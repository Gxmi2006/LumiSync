# LumiSync

[![Windows](https://img.shields.io/badge/platform-Windows%2011-0A84FF?style=flat-square)](#requirements)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)](https://www.python.org/)
[![RGB](https://img.shields.io/badge/RGB-Aura%20%7C%20OpenRGB-7C3AED?style=flat-square)](#rgb-backend-setup)
[![License](https://img.shields.io/badge/license-MIT-111827?style=flat-square)](#license)

**A lightweight open-source ambient RGB synchronization engine for Windows.**

LumiSync samples colors from games, movies, browsers, streaming apps, desktop windows, and displays, then translates them into smooth low-latency RGB lighting for Aura-compatible ASUS devices and OpenRGB ecosystems. It is designed to feel like a laptop-friendly, open-source ambient lighting layer: simple to run, easy to configure, and safe even when no hardware backend is available.

> Comparable in spirit to Ambilight, LIGHTSYNC ambient effects, Razer Ambient Awareness, Hyperion, Prismatik, and SignalRGB ambient sync, but focused on being smaller, transparent, Python-hackable, and friendly to laptops.

## Highlights

- Sync RGB from the foreground window, a named app window, a custom region, or a monitor.
- Extract dominant colors with OpenCV + NumPy while ignoring dark UI noise.
- Smooth color transitions to avoid flicker and harsh jumps.
- Dispatch to ASUS Aura / Armoury Crate COM first, then OpenRGB SDK when available.
- Continue running in software fallback mode when no RGB backend or device exists.
- Tray app, global hotkeys, debug capture overlay, startup shortcut support, and reconnect handling.
- Designed for gaming, YouTube, anime, movies, emulators, desktop themes, productivity dashboards, and experimentation.

## Demo Media Placeholders

Add these assets before a public launch:

- `assets/demo-game.gif`: foreground game window driving keyboard colors at 20-30 FPS.
- `assets/demo-movie.gif`: cinematic mode reacting smoothly to letterboxed video.
- `assets/demo-overlay.png`: debug overlay showing capture rectangle, FPS, color, and backend state.
- `assets/backend-report.png`: startup diagnostics showing Aura, OpenRGB, and software fallback statuses.
- `assets/social-preview.png`: dark minimalist banner with LumiSync wordmark, RGB edge glow, and laptop silhouette.

## Project Overview

Ambient RGB sync works by sampling pixels from visual content, reducing those pixels into one or more representative colors, smoothing the output over time, and sending color updates to RGB devices. LumiSync keeps that pipeline explicit:

1. Select a capture target: active window, named window, monitor, or region.
2. Capture only the needed pixels with `mss`.
3. Downscale frames before processing.
4. Filter near-black, low-saturation, and sparse noise pixels.
5. Extract a dominant color or multi-region palette with OpenCV + NumPy.
6. Apply smoothing, brightness controls, and optional effects.
7. Dispatch to Aura, OpenRGB, or software fallback.

Supported RGB ecosystems today:

- ASUS Aura / Armoury Crate COM SDK using ProgID `aura.sdk.1`.
- OpenRGB SDK server on `127.0.0.1:6742`.
- Software fallback mode for diagnostics, development, and unsupported hardware.

Hardware assumptions are intentionally conservative. LumiSync does not assume your keyboard is exposed by Aura or OpenRGB. If no RGB device is detected, it logs a clear report and keeps the capture engine alive.

## Features

- **Monitor sync:** capture an entire display via MSS monitor indexes.
- **Window sync:** track foreground windows or target windows by process/title.
- **Fullscreen-aware targeting:** structure is ready for profile switching around fullscreen apps.
- **Region capture:** crop by ratios and pixel offsets for HUDs, video panes, emulator screens, or browser players.
- **Edge sampling direction:** planned Ambilight-style edge mode with monitor edge mapping.
- **Dominant color extraction:** weighted quantized histogram extraction with black/saturation filtering.
- **Multi-zone gradients:** split captured frames into horizontal/vertical regions and dispatch per-zone colors where supported.
- **Smoothing engine:** exponential interpolation tuned for no flicker and low perceived latency.
- **Adaptive brightness hooks:** normalization and cinematic dark-scene handling extension points.
- **Low-latency updates:** configurable 10-30 FPS with update throttling and color-delta suppression.
- **OpenRGB integration:** SDK server probing, timeout handling, keyboard filtering, and reconnect retries.
- **Aura integration:** COM detection, `SwitchMode()`, device enumeration, no-device reporting, and safe failures.
- **Software fallback:** capture and processing always run even without hardware.
- **Tray app:** quick pause, reload config, toggle overlay, and quit controls.
- **Global hotkeys:** pause/resume, reload, debug overlay, quit.
- **Debug overlays:** capture rectangle, detected color, FPS, backend, and status.
- **Startup integration:** install or remove Windows Startup shortcut.
- **Profile system:** TOML profile sections are defined for gaming, movies, low-power laptops, and cinematic modes.
- **Presets:** repository structure includes a presets namespace for future built-in profiles.

## Architecture

```text
lumisync/
  core/          app loop, config, color primitives, smoothing, logging, optional websocket API
  capture/       window detection, monitor detection, region capture, monitor capture
  processing/    palette extraction and frame reduction
  backends/      Aura/OpenRGB/software fallback backend manager
  effects/       adaptive brightness, audio-reactive hooks, effect pipeline
  ui/            tray icon and hotkeys
  overlays/      debug overlay
  diagnostics/   status and environment reports
  profiles/      profile manager
  presets/       future built-in profile catalog
  utils/         Windows startup helpers
```

Runtime flow:

```text
target selection -> capture -> downscale -> pixel filtering -> palette extraction
-> smoothing/effects -> backend manager -> Aura/OpenRGB/software fallback
```

The backend manager is the only place that touches RGB SDKs. Aura and OpenRGB can fail, time out, or report no devices without affecting capture, processing, tray, overlay, or hotkeys.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the long-form architecture plan.

## Requirements

- Windows 11
- Python 3.10+
- Optional: Armoury Crate / Aura components for ASUS Aura control
- Optional: OpenRGB with SDK server enabled

Python libraries:

- `pywin32`, `psutil`, `mss`
- `numpy`, `opencv-python`, `pillow`
- `openrgb-python`
- `pystray`, `keyboard`
- `pycaw` for optional audio-reactive brightness pulsing

## Installation

````markdown
# PowerShell Fix for `Activate.ps1` Script Error

If you see an error like:

```powershell
running scripts is disabled on this system
````

PowerShell is blocking virtual environment activation scripts.

---

## Fix (Recommended)

Open **PowerShell** and run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

When prompted, type:

```powershell
Y
```

Then activate the virtual environment again:

```powershell
.\.venv\Scripts\Activate.ps1
```

You should now see:

```powershell
(.venv) PS C:\...
```

---

## Temporary Fix (No Permanent Changes)

If you do not want to change the system policy permanently:

```powershell
Set-ExecutionPolicy Bypass -Scope Process
```

Then activate:

```powershell
.\.venv\Scripts\Activate.ps1
```

This only affects the current PowerShell session.

---

## Full Setup Commands

```powershell
py -3.11 -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

python -m pip install -r requirements.txt
```

---

## Why This Happens

Windows PowerShell blocks unsigned local scripts by default for security reasons.

`Activate.ps1` is considered a script, so PowerShell prevents it from running until execution policy allows local scripts.

```
```


Run LumiSync:

```powershell
python -m lumisync --config .\config.toml
```

Legacy compatibility still works:

```powershell
python -m konsl_aura_sync --config .\config.toml
```

Logs are written to `%APPDATA%\LumiSync\logs\lumisync.log`.

## Usage

Sync the foreground app:

```toml
[app]
capture_mode = "active_window"

[window]
process_name = ""
title_contains = ""
```

Sync a game window:

```toml
[window]
process_name = "Game.exe"
title_contains = ""
```

Sync a browser video:

```toml
[window]
process_name = "chrome.exe"
title_contains = "YouTube"
```

Sync a centered video or emulator region:

```toml
[capture]
left_ratio = 0.12
top_ratio = 0.08
width_ratio = 0.76
height_ratio = 0.82
```

Use the debug overlay while tuning:

```powershell
python -m lumisync --config .\config.toml --debug-overlay
```

List matching windows:

```powershell
python -m lumisync --list-windows
```

Test a hardware backend color:

```powershell
python -m lumisync --test-color 22CCFF
```

## Configuration

The default [config.toml](config.toml) is commented and includes stable sections for:

- `app`, `capture`, `monitor`, `window`
- `processing`, `smoothing`, `performance`
- `rgb`, `aura`, `openrgb`
- `effects`, `gradient`, `audio_pulse`
- `overlay`, `diagnostics`, `startup`, `logging`
- `profiles.default`, `profiles.gaming`, `profiles.movie`, `profiles.low_power_laptop`, `profiles.cinematic`

Common tuning:

- Lower `app.fps` to reduce CPU and battery usage.
- Raise `smoothing.strength` for slower cinematic transitions.
- Lower `smoothing.strength` for responsive gaming.
- Raise `processing.black_threshold` to ignore dark UI backgrounds.
- Raise `processing.saturation_multiplier` for more vivid keyboard output.
- Reduce `processing.downscale_width/downscale_height` for lower CPU.

Deep config documentation lives in [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## RGB Backend Setup

### ASUS Aura / Armoury Crate

LumiSync uses the Aura COM ProgID `aura.sdk.1`. On startup it:

1. Imports COM support from `pywin32`.
2. Creates the Aura SDK COM object.
3. Calls `SwitchMode()`.
4. Enumerates configured keyboard and notebook keyboard device types.
5. Reports `available`, `no devices`, `not found`, `disabled`, or `error`.

Many ASUS laptops have Armoury Crate installed but do not expose the keyboard through the public Aura SDK. LumiSync handles this as `Aura: no devices` and continues in OpenRGB or software fallback mode.

### OpenRGB

OpenRGB requires its SDK server:

1. Open OpenRGB.
2. Open the SDK Server tab.
3. Start the server, or launch OpenRGB with `--server`.
4. Keep `address = "127.0.0.1"` and `port = 6742` unless you changed OpenRGB.

LumiSync probes the server with a timeout before creating the SDK client. It reports `connected`, `not running`, `timeout`, `not found`, `no devices`, `disabled`, or `error`.

### Software Fallback

Software fallback is intentional. It means:

- capture still runs
- color extraction still runs
- debug overlay still works
- tray and hotkeys still work
- no hardware writes are attempted

Example startup report:

```text
LumiSync backend status:
  Aura: no devices - Aura SDK is installed, but it reported no supported keyboard lighting devices
  OpenRGB: timeout - OpenRGB SDK server probe ended with timeout
  Active backend: software fallback
```

## Hotkeys

- `Ctrl+Alt+P`: pause/resume sync
- `Ctrl+Alt+R`: reload config
- `Ctrl+Alt+D`: toggle debug overlay
- `Ctrl+Alt+Q`: quit

The `keyboard` package may need administrator privileges on some Windows systems.

## Performance Optimization

LumiSync is designed around bounded per-frame work:

- capture only the selected window/region
- downscale before OpenCV processing
- ignore sparse masks to avoid noise
- throttle RGB writes by interval and color delta
- smooth in RGB space with minimal allocations

Suggested profiles:

- **Gaming:** `fps = 30`, smoothing `0.40-0.50`, downscale `160x90`
- **Movies/anime:** `fps = 16-20`, smoothing `0.70-0.85`, higher black threshold
- **Battery laptop:** `fps = 10`, downscale `96x54`, update interval `50ms`

Future engine work includes DXcam/Desktop Duplication capture, adaptive FPS, dirty-region detection, and separate capture/process/dispatch threads. See [docs/ENGINEERING.md](docs/ENGINEERING.md).

## Troubleshooting

**Aura says `no devices`**

Armoury Crate can be installed while the public Aura SDK exposes no keyboard device. Use software fallback, try OpenRGB, or check whether your laptop model exposes notebook keyboard device types through Aura.

**OpenRGB says `not running` or `timeout`**

Start the OpenRGB SDK server and confirm `127.0.0.1:6742`. If the app is slow to report startup status, reduce `openrgb.connection_timeout_seconds`.

**No color changes, but the app runs**

Check the startup backend report. If active backend is `software fallback`, the capture pipeline is healthy but no hardware backend is connected.

**Colors flicker**

Raise `smoothing.strength`, raise `rgb.minimum_color_delta`, or reduce `app.fps`.

**Colors are too dark**

Lower `processing.black_threshold` or raise `processing.brightness_multiplier`.

**Wrong content is sampled**

Enable the debug overlay, then tune `[window]` and `[capture]` ratios.

**CPU usage is too high**

Lower FPS, reduce downscale resolution, or narrow the capture region.

## Build

```powershell
.\build.ps1
```

The executable is produced at:

```text
dist\LumiSync\LumiSync.exe
```

Run:

```powershell
.\dist\LumiSync\LumiSync.exe --config .\config.toml
```

## Roadmap

- Monitor edge mapping and Ambilight-style multi-zone output.
- DXcam/Desktop Duplication capture backend.
- Automatic fullscreen detection and profile switching.
- WLED, Philips Hue, Nanoleaf, MQTT, and REST/WebSocket integrations.
- Plugin API for capture sources, effects, and RGB backends.
- OBS and Stream Deck integrations for creators.
- Profile editor UI and signed Windows builds.

See [docs/FEATURE_EXPANSION.md](docs/FEATURE_EXPANSION.md) and [docs/VISION.md](docs/VISION.md).

## Contributing

LumiSync is intentionally modular. Good first contribution areas:

- add capture targets
- improve device detection
- add OpenRGB device mappings
- tune processing profiles
- build screenshots and demo GIFs
- write backend diagnostics
- improve docs for specific hardware

Read [docs/GITHUB_ECOSYSTEM.md](docs/GITHUB_ECOSYSTEM.md) for issue templates, labels, release strategy, and repository growth polish.

## License

MIT License. See `LICENSE` when added.

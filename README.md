# LumiSync

[![Windows 11](https://img.shields.io/badge/Windows-11-0A84FF?style=flat-square)](#requirements)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](#quick-start)
[![OpenRGB](https://img.shields.io/badge/OpenRGB-SDK%20Server%20Required-22C55E?style=flat-square)](#openrgb-setup)
[![PyInstaller](https://img.shields.io/badge/Build-PyInstaller-111827?style=flat-square)](#build)
[![License](https://img.shields.io/badge/License-MIT-111827?style=flat-square)](#license)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-support-FF5E5B?style=flat-square&logo=kofi&logoColor=white)](https://ko-fi.com/gamindusasmitha)

**Lightweight ambient RGB for Windows. It reads the colors on your screen and sends the best one to your OpenRGB devices.**

LumiSync watches your games, movies, browser videos, anime, emulators, windows, and monitors, picks the color that actually matters in the scene, and fades your keyboard, strips, and case lighting to match. It is built for people who want ambient RGB without a heavy vendor suite.

**If OpenRGB supports your device, LumiSync supports it.** Keyboards, mice, fans, fan hubs, motherboards, RAM, GPUs and LED strips all work the same way. Check the [OpenRGB supported devices list](https://openrgb.org/devices.html) for your hardware.

```text
game / movie / browser / window
        -> grab a small region, shrunk at capture time
        -> find the focal object, or fall back to scene harmony
        -> smooth the color and style the palette
        -> send one best color to OpenRGB (or run in software fallback)
```

## Highlights

| | |
| --- | --- |
| **Picks the right color** | Finds glowing objects, neon rings, and bright highlights instead of averaging the whole frame into mud. |
| **Calm by default** | One cinematic color, low-flicker smoothing, and update throttling. No flashy gradients unless you turn them on. |
| **Light on your PC** | Frames are shrunk to 160x90 before analysis, regions are ranked before they are scored, and the loop slows down when the scene is static. |
| **Works with your hardware** | If OpenRGB supports it, LumiSync supports it: keyboards, mice, fans, fan hubs, motherboards, RAM, GPUs, LED strips and laptops. Falls back to all devices if no keyboard matches. |
| **Never crashes without hardware** | If OpenRGB is not running, capture and color analysis keep going in software fallback and reconnect later. |
| **Easy to tune and debug** | Plain `config.toml`, a debug overlay, global hotkeys, tray icon, `--diagnostics`, and `--setup-check`. |

## Optimized by design

LumiSync is meant to sit in the background while you play or watch something, so each stage of the loop is kept cheap.

| Optimization | What it does for you |
| --- | --- |
| Capture-time downscaling | The screen grab is shrunk straight from the capture buffer, so no full-resolution RGB copy is made each frame. |
| Region pre-ranking | On busy or grainy frames, only the strongest few candidate regions are fully scored instead of every one. |
| Cheap palette selection | Partial sorting and direct weighted means replace full sorts and generic averaging. |
| Adaptive FPS | After 3 seconds of an unchanging color, the loop drops to `idle_fps`, then returns to full speed as soon as the scene moves. |
| Update throttling | `minimum_update_interval_ms` and `minimum_color_delta` stop redundant writes to your RGB hardware. |
| Debug work on demand | Overlay data is only built while the debug overlay is on. |
| Quiet tray icon | The tray icon repaints at most twice a second, and only for visible color changes. |

Measured on one test machine (1920x1200 display, Python 3.14), comparing the previous release with this one:

| Stage | Before | After |
| --- | ---: | ---: |
| Color extraction on a busy, grainy frame | 22.5 ms | 15.5 ms |
| Color extraction on a typical game-like frame | 7.3 ms | 6.4 ms |
| Whole frame (capture, extraction, smoothing) | 36.1 ms | 34.1 ms |
| Slowest frame observed | 47.9 ms | 39.3 ms |

The Windows screen grab itself takes about 28 ms on that display and scales with the captured area. That is why the biggest wins for you are a smaller capture region, a sensible FPS, and adaptive FPS (see [Optimized usage](#optimized-usage)). Your numbers will vary with display size and hardware.

## Requirements

- Windows 11
- Python 3.10+ for source installs
- OpenRGB for hardware output, with the SDK Server enabled
- Optional: PyInstaller for standalone executable builds

## Quick Start

1. Install [OpenRGB](https://openrgb.org/), open the **SDK Server** tab, and click **Start Server** (default port 6742).
2. Install LumiSync:

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

3. Check your setup, then run:

```powershell
python -m lumisync --setup-check
python -m lumisync --config .\config.toml
```

`--setup-check` verifies dependencies, the OpenRGB SDK Server, detected devices, hotkey support, and config safety, and prints exact fix steps. `--diagnostics` shows what LumiSync detected. You want to see:

```text
OpenRGB: connected - ready for hardware RGB updates
Active backend: openrgb
```

If OpenRGB is not running, LumiSync enters **software fallback**: capture, color extraction, tray controls, hotkeys, and the overlay still work, but no hardware writes are sent.

## Smart Color Engine

LumiSync does not just average the screen.

**Focal mode.** When a scene has an obvious subject, LumiSync prioritizes it: neon rings and glow, saturated foreground objects, white and gray highlight rings, cinematic highlights, high-contrast edges, centered subjects, and regions that stay stable over time. A dark scene with a glowing green ring outputs the ring color, not muddy dark blue.

**Scene harmony mode.** When no single object wins, LumiSync filters near-black and dull pixels, groups colors into HSV families, scores them by vividness, coverage, brightness, contrast, and elegance, and picks the best scene color instead of a raw average.

```toml
[palette]
fallback_mode = "scene_harmony"
multi_color_mode = "cinematic"
minimum_focal_confidence = 0.35
palette_size = 1
harmony_strength = 0.35
```

| Palette mode | Result |
| --- | --- |
| `scene` | Uses colors sampled from the current frame |
| `harmonic` | Generates analogous colors around the selected hue |
| `cinematic` | Default. Restrained, lower-brightness styling |

## Features

| Area | Capabilities |
| --- | --- |
| Capture | Active-window sync, process/title targeting, normalized region capture, monitor detection |
| Color engine | Saliency detection, focal region scoring, scene-harmony fallback, OpenCV/NumPy palette extraction |
| Output | One best cinematic color by default, optional multi-zone gradients |
| Smoothing | Low-flicker interpolation, update throttling, configurable and adaptive FPS |
| OpenRGB | Any OpenRGB-supported device, including RGB fans and fan hubs. SDK Server connection, reconnect handling, all-device fallback |
| Desktop app | Tray icon, global hotkeys, debug overlay, startup shortcut |
| Reliability | Software fallback, structured diagnostics, rotating logs |
| Packaging | PyInstaller build for a standalone Windows executable |

## Optimized usage

Pick the recipe that matches what you are doing and paste it into `config.toml`. Every key below already exists in the file.

### The biggest levers

1. **Capture less.** Screen grab time grows with the captured area. Sample only the video or game area with `[capture]` ratios, or sync one window instead of a whole monitor.
2. **Lower the FPS.** Ambient light does not need 60 updates a second. 16-20 FPS looks smooth for video, 24-30 for games.
3. **Keep adaptive FPS on.** Static scenes (menus, paused video, desktop) cost almost nothing.
4. **Keep the analysis small.** The default 160x90 is enough. Going lower saves little and loses accuracy.
5. **Let the hardware rest.** A higher `minimum_color_delta` means fewer writes to OpenRGB.

### Recipe: everyday balanced

```toml
[app]
fps = 20
capture_mode = "active_window"

[performance]
adaptive_fps = true
idle_fps = 5
max_fps = 30

[rgb]
minimum_update_interval_ms = 16
minimum_color_delta = 2.0
```

### Recipe: gaming (fast reactions)

```toml
[app]
fps = 30
capture_mode = "active_window"

[smoothing]
strength = 0.42

[processing]
brightness_multiplier = 0.92
saturation_multiplier = 1.18
black_threshold = 22

[performance]
max_fps = 30
```

### Recipe: movies and anime (smooth and cinematic)

```toml
[app]
fps = 18
capture_mode = "monitor"

[smoothing]
strength = 0.76

[processing]
black_threshold = 32

[capture]
# Skip letterbox and subtitle bars by sampling the middle of the frame.
top_ratio = 0.10
height_ratio = 0.80
```

### Recipe: battery laptop (lowest overhead)

```toml
[app]
fps = 10

[processing]
downscale_width = 96
downscale_height = 54

[smoothing]
strength = 0.70

[rgb]
minimum_update_interval_ms = 50
minimum_color_delta = 4.0

[performance]
adaptive_fps = true
idle_fps = 3
```

### Recipe: quiet hardware (fewer writes)

```toml
[rgb]
minimum_update_interval_ms = 40
minimum_color_delta = 5.0

[smoothing]
strength = 0.80
```

### Quick tuning cheat sheet

| You want | Change |
| --- | --- |
| Lower CPU use | Lower `app.fps`, shrink the `[capture]` area, lower `performance.idle_fps` |
| Smoother, less flicker | Raise `smoothing.strength` (0.72-0.84) and `rgb.minimum_color_delta` |
| Faster reactions | Lower `smoothing.strength` (0.40-0.50) and raise `app.fps` |
| Fewer RGB writes | Raise `rgb.minimum_update_interval_ms` and `rgb.minimum_color_delta` |
| Never slow down | Set `performance.adaptive_fps = false` |
| Cap the loop | Set `performance.max_fps` |

`config.toml` also contains `[profiles.*]` blocks (default, gaming, movie, low_power_laptop, cinematic) with the same kind of value sets. Profile switching is not wired into the app yet, so copy the values you want into the main sections for now.

### Performance settings reference

| Key | Default | Meaning |
| --- | ---: | --- |
| `performance.adaptive_fps` | `true` | Drop to `idle_fps` after 3 seconds of an unchanging color |
| `performance.idle_fps` | `5` | Loop rate while the scene is static (1-30) |
| `performance.max_fps` | `30` | Upper limit for the loop (1-60), applied on top of `app.fps` |
| `app.fps` | `20` | Target loop rate while the scene is changing |
| `processing.downscale_width/height` | `160x90` | Analysis resolution |
| `rgb.minimum_update_interval_ms` | `16` | Shortest gap between hardware writes |
| `rgb.minimum_color_delta` | `2.0` | Smallest color change worth sending |

## OpenRGB Setup

OpenRGB is the default hardware backend, and LumiSync sends its color to every device OpenRGB can control. If a device shows up and changes color in OpenRGB, LumiSync can drive it, whether it is a keyboard, mouse, fan, fan hub, motherboard, RAM kit, GPU, LED strip or laptop. Look up your hardware on the [OpenRGB supported devices list](https://openrgb.org/devices.html).

1. Install OpenRGB.
2. Start OpenRGB.
3. Open **SDK Server**.
4. Click **Start Server**.
5. Run:

```powershell
python -m lumisync --diagnostics
```

Run the setup checker when onboarding or debugging another PC:

```powershell
python -m lumisync --setup-check
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

### RGB Fans

RGB fans work through OpenRGB, the same way as every other device.

- **Fans on a motherboard ARGB header** show up under your motherboard in OpenRGB. In OpenRGB, select the ARGB header zone and use **Resize Zone** to set the LED count your fans have, or they may light up partly or not at all.
- **Fans on a fan/RGB hub** (Corsair Commander, Lian Li Uni Hub, NZXT and similar) work if OpenRGB supports that hub. Check the [OpenRGB supported devices list](https://openrgb.org/devices.html).
- Fans that only work with a remote or a hub that has no OpenRGB support can't be controlled.

LumiSync picks up fans automatically: motherboard and cooler/hub devices are matched by their OpenRGB device type, and `fan` and `cooler` are in the default `device_name_contains` list. If your fans still stay dark, run `python -m lumisync --diagnostics` to see which devices were selected, then add part of the device's name to `device_name_contains` in `config.toml`, or set `prefer_keyboard_devices = false` to drive every OpenRGB device.

Close iCUE, Armoury Crate, L-Connect, NZXT CAM and other vendor RGB apps while LumiSync runs, because they fight OpenRGB for control. All fans show one color by default; see the gradient options in [Configuration](#configuration) for multi-zone output.

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

Sync a whole monitor:

```toml
[app]
capture_mode = "monitor"

[monitor]
index = 1
```

Sync a custom desktop region:

```toml
[app]
capture_mode = "region"

[capture]
left_ratio = 0.10
top_ratio = 0.08
width_ratio = 0.80
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

### A bright, white, or gray object is being missed

Lower the focal threshold:

```toml
[visual_priority]
saliency_threshold = 0.28

[palette]
minimum_focal_confidence = 0.30
```

If white/gray UI text wins too often, raise `minimum_focal_confidence` slightly or narrow `[capture]` to the video/visualizer area.

### Colors flicker

```toml
[smoothing]
strength = 0.72

[rgb]
minimum_color_delta = 4.0
```

### Wrong screen area is sampled

Run with `--debug-overlay`, then tune `[window]` and `[capture]`.

### First-time setup is confusing

Run:

```powershell
python -m lumisync --setup-check
```

It checks dependencies, OpenRGB SDK Server, devices, hotkeys, and config values.

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
  diagnostics/  backend/runtime reports and setup checks
  profiles/     profile loading
  utils/        Windows startup helpers
```

The backend manager is the only layer that talks to RGB SDKs. Capture and color processing continue even if OpenRGB is unavailable.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Roadmap

- Monitor and region capture refinements
- Edge sampling and Ambilight-style zone mapping
- DXcam/Desktop Duplication capture backend
- Automatic fullscreen detection and profile switching
- WLED, Philips Hue, and Nanoleaf backends
- WebSocket/REST API
- OBS and Stream Deck integrations
- GUI profile editor
- Signed Windows builds

## Known Limitations

- OpenRGB must expose the device before LumiSync can control it.
- The packaged `LumiSync.exe` is windowed for background use; run source commands from PowerShell when you need visible diagnostics output.
- Aura / Armoury Crate support is legacy opt-in and may report no devices on many ASUS laptops.
- Windows capture is based on visible desktop pixels; protected video surfaces or minimized windows may not capture useful frames.
- Multi-color zone gradients are available in code but disabled by default to keep the default experience calm and single-color.

## Contributing

Good areas to help:

- test OpenRGB behavior on real hardware
- improve scene harmony and visual-priority scoring
- add capture backends
- improve zone mapping for keyboards and LED strips
- create screenshots and demo GIFs
- write hardware-specific setup guides

See [docs/GITHUB_ECOSYSTEM.md](docs/GITHUB_ECOSYSTEM.md) for labels, issue templates, release naming, and project presentation ideas.

## Support LumiSync

LumiSync is free and open source. If it makes your setup better and you would like to help keep it going, you can [support me on Ko-fi](https://ko-fi.com/gamindusasmitha). Starring the repo, reporting bugs and sharing it with other RGB fans helps a lot too.

## Credits

- Promo reel voice-over generated with [ElevenLabs](https://elevenlabs.io) text-to-speech (voice: Liam).
- Promo reel animated with [Remotion](https://www.remotion.dev) and [Three.js](https://threejs.org). Source in [`marketing/`](marketing/).
- RGB hardware control through [OpenRGB](https://openrgb.org).

## License

MIT License. See [LICENSE](LICENSE).

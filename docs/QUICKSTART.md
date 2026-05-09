# Quick Start

## 1. Start OpenRGB SDK Server

1. Install OpenRGB.
2. Open OpenRGB.
3. Go to **SDK Server**.
4. Click **Start Server**.

The default LumiSync config expects:

```toml
[openrgb]
address = "127.0.0.1"
port = 6742
```

## 2. Install LumiSync

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Run Diagnostics

```powershell
python -m lumisync --diagnostics
```

You want to see:

```text
OpenRGB: connected
Active backend: openrgb
```

If OpenRGB is not running, LumiSync will use software fallback and keep the capture/color pipeline alive.

## 4. Run Ambient Sync

```powershell
python -m lumisync --config .\config.toml
```

Put a game, video, browser, or emulator window in focus.

## 5. Tune A Window

```powershell
python -m lumisync --config .\config.toml --debug-overlay
```

Adjust:

```toml
[window]
process_name = "chrome.exe"
title_contains = "YouTube"

[capture]
left_ratio = 0.10
top_ratio = 0.08
width_ratio = 0.80
height_ratio = 0.82
```

Press `Ctrl+Alt+R` to reload config.

## 6. Multi-Color Keyboard Output

The default config sends a 3-color scene palette to OpenRGB zones or LEDs when the device supports it:

```toml
[gradient]
enabled = true
send_regions_to_zones = true

[palette]
multi_color_mode = "scene"
palette_size = 3
```

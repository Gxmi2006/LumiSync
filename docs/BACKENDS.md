# RGB Backend Guide

LumiSync is OpenRGB-first. Visual processing is separate from hardware control, so capture and color extraction keep running even when no RGB backend is available.

## Default Backend Order

With the default config:

```toml
[app]
controller = "openrgb"
```

LumiSync:

1. Connects to the OpenRGB SDK Server.
2. Selects preferred keyboard/laptop-like devices when available.
3. Falls back to all OpenRGB devices if no preferred match exists and `allow_all_devices_if_no_keyboard = true`.
4. Uses software fallback if OpenRGB is unavailable.

Aura is not probed by default.

## OpenRGB Setup

Installing OpenRGB is not enough. The SDK Server must be running.

1. Install OpenRGB.
2. Open OpenRGB.
3. Open the **SDK Server** tab.
4. Click **Start Server**.
5. Confirm the LumiSync config:

```toml
[openrgb]
address = "127.0.0.1"
port = 6742
allow_all_devices_if_no_keyboard = true
```

Common statuses:

- `connected`: LumiSync connected and selected at least one usable device.
- `not running`: OpenRGB SDK Server is not listening.
- `timeout`: the server did not respond in time.
- `no devices`: OpenRGB connected but exposed no usable devices.
- `not found`: the Python OpenRGB client is not installed.

## Multi-Color Output

When OpenRGB exposes zones or LEDs, LumiSync sends a palette instead of only one color:

```toml
[gradient]
enabled = true
regions = 3
send_regions_to_zones = true

[palette]
multi_color_mode = "cinematic"
palette_size = 3
```

Unsupported devices receive the best single color automatically.

## Software Fallback

Software fallback means:

- capture runs
- visual priority runs
- scene harmony runs
- debug overlay works
- tray and hotkeys work
- no hardware writes are attempted

Use fallback to tune capture regions and color settings before hardware is ready.

## ASUS Aura Legacy Mode

Aura / Armoury Crate support remains available for advanced users but is disabled by default because many ASUS laptops do not expose keyboard devices through the public Aura SDK.

To try Aura manually:

```toml
[app]
controller = "aura"

[aura]
enabled = true
```

Common statuses:

- `available`: Aura is controlling at least one matching keyboard device.
- `no devices`: Aura exists but did not expose a supported keyboard.
- `not found`: Aura COM support or `pywin32` is missing.
- `error`: Aura started but failed during discovery or update.

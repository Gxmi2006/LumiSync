# RGB Backend Guide

LumiSync separates visual processing from RGB hardware control. If hardware control fails, the app continues in software fallback mode.

## Backend Order

When `app.controller = "auto"`:

1. Aura is attempted first.
2. OpenRGB is attempted if Aura is unavailable or reports no devices.
3. Software fallback is activated if no hardware backend works.

Set `diagnostics.probe_all_backends = true` if you want diagnostics to probe OpenRGB even when Aura succeeds.

## OpenRGB

OpenRGB requires the SDK Server.

1. Install OpenRGB.
2. Open OpenRGB.
3. Open the **SDK Server** tab.
4. Click **Start Server**.
5. Confirm the LumiSync config:

```toml
[openrgb]
address = "127.0.0.1"
port = 6742
```

Common statuses:

- `connected`: LumiSync connected and found a matching device.
- `not running`: OpenRGB SDK Server is not listening.
- `timeout`: the server did not respond in time.
- `no devices`: OpenRGB connected, but no matching keyboard/device was selected.
- `not found`: the Python OpenRGB client is not installed.

## ASUS Aura / Armoury Crate

Aura support uses the Windows COM ProgID `aura.sdk.1`.

Common statuses:

- `available`: Aura is controlling at least one matching keyboard device.
- `no devices`: Aura exists but did not expose a supported keyboard.
- `not found`: Aura COM support or `pywin32` is missing.
- `error`: Aura started but failed during discovery or update.

`no devices` is common on some ASUS laptops. It does not mean LumiSync is broken.

## Software Fallback

Software fallback means:

- capture runs
- visual priority runs
- debug overlay works
- tray and hotkeys work
- no hardware writes are attempted

Use fallback to tune capture regions and visual-priority settings before hardware is ready.

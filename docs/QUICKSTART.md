# Quick Start

## With OpenRGB

1. Install dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Open OpenRGB.
3. Go to **SDK Server**.
4. Click **Start Server**.
5. Run LumiSync:

```powershell
python -m lumisync --config .\config.toml
```

## With ASUS Aura / Armoury Crate

1. Install Armoury Crate / Aura components.
2. Install Python dependencies.
3. Run:

```powershell
python -m lumisync --diagnostics
```

If Aura reports `no devices`, try OpenRGB or continue in software fallback mode.

## Tune A Window

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

# LumiSync Brand Package

## Repository Description

Lightweight open-source ambient RGB synchronization engine for Windows. Sync Aura/OpenRGB lighting with games, movies, browsers, monitors, and application windows.

## Elevator Pitch

LumiSync is a small, hackable Windows ambient RGB engine that samples colors from whatever you are watching or playing and turns them into smooth RGB lighting. It keeps the pipeline transparent: capture pixels, extract a palette, smooth the signal, and dispatch to Aura, OpenRGB, or software fallback. It is built for gamers, laptop users, creators, and RGB enthusiasts who want ambient sync without a heavy closed ecosystem.

## Tagline Variations

- Ambient RGB sync, without the bloat.
- Open-source Ambilight for your Windows desktop.
- Lightweight RGB that follows what you play and watch.
- A modular ambient lighting engine for games, movies, and monitors.
- RGB sync for people who like knowing how things work.

## Branding Tone

LumiSync should feel premium but not corporate, technical but not intimidating, and gamer-friendly without loud visual clutter. The voice is calm, precise, minimalist, and open-source-native. It should communicate that the project is lightweight, trustworthy, configurable, and engineered by people who care about latency, battery life, and clean abstractions.

## Target Audience

- Laptop gamers who want ambient RGB without installing a full RGB suite.
- OpenRGB users who want window/monitor-based ambient sync.
- ASUS Armoury Crate users whose keyboard support is inconsistent.
- Movie, anime, YouTube, and streaming users who want subtle immersive lighting.
- Emulator and retro gaming users.
- Streamers who want lighting automation hooks.
- Python contributors who want a practical Windows desktop project.
- Hardware enthusiasts who want transparent diagnostics and fallback behavior.

## Unique Selling Points

- Runs even when no RGB backend exists, which makes diagnostics and tuning safe.
- Aura and OpenRGB support are treated as optional backends, not assumptions.
- Low-overhead Python pipeline using MSS, OpenCV, and NumPy.
- Window-first design for laptop users rather than only whole-monitor LED strips.
- Debug overlay makes capture tuning visible and approachable.
- TOML profiles make advanced behavior editable without a GUI.
- Modular structure for capture sources, effects, profiles, and RGB backends.

## Competitive Positioning

LumiSync is not trying to replace every feature in SignalRGB or vendor suites on day one. Its wedge is being lighter, more transparent, and easier to extend. It fits between heavyweight RGB ecosystems and one-off scripts:

- Compared with SignalRGB: smaller scope, open Python code, simpler diagnostics, laptop-friendly.
- Compared with OpenRGB: uses OpenRGB as a backend but adds capture, palette, smoothing, profiles, and ambient logic.
- Compared with vendor suites: avoids lock-in, keeps fallback behavior safe, exposes config directly.
- Compared with Hyperion/Prismatik: Windows desktop/window workflow first, not only LED strip/TV bias lighting.

## Why This Project Exists

RGB sync software is often closed, vendor-specific, heavy, or brittle around laptops. LumiSync exists because ambient lighting should be understandable, portable across RGB backends, and usable even when hardware APIs are inconsistent. The project turns a narrow visualizer sync app into a general-purpose ambient engine with clear failure modes and room for community backends.

## Project Philosophy

- Capture narrowly before processing heavily.
- Prefer clear diagnostics over silent hardware failures.
- Treat every RGB backend as optional and unreliable.
- Keep the pipeline modular enough for contributors to replace one stage.
- Make low CPU usage a feature, not an afterthought.
- Design for laptops, not only desktop towers and LED strips.
- Prefer configuration and profiles before building a complex GUI.

## Key Differentiators

- Software fallback is a first-class mode.
- Backend detection is centralized and reportable.
- Capture is window/region aware rather than full-screen-only.
- Effects are planned as stackable pipeline stages.
- The project is Python-native and approachable for contributors.
- The repository is positioned as an engine, not just a single hardware script.

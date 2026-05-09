from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from lumisync.core.config_writer import resolve_active_config_path, write_config_settings
from lumisync.core.theme_presets import ThemeSelection, build_theme_settings, describe_settings
from lumisync.ui.setup_wizard import run_setup_wizard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumisync-setup",
        description="Configure LumiSync theme and OpenRGB color preferences.",
    )
    parser.add_argument("--config", help="Path to config.toml")
    parser.add_argument("--dry-run", action="store_true", help="Print selected settings without writing config")
    parser.add_argument("--save", action="store_true", help="Save selected settings without opening the GUI")
    parser.add_argument("--mood", choices=["cinematic", "balanced", "vivid", "low_power"], default="cinematic")
    parser.add_argument("--multicolor", choices=["elegant", "single", "auto"], default="elegant")
    parser.add_argument("--content", choices=["movies", "games", "desktop"], default="movies")
    parser.add_argument("--intensity", choices=["subtle", "normal", "bold"], default="subtle")
    parser.add_argument("--device", choices=["keyboard", "all"], default="keyboard")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config).resolve() if args.config else None
    selection = ThemeSelection(
        mood=args.mood,
        multicolor=args.multicolor,
        content=args.content,
        intensity=args.intensity,
        device_preference=args.device,
    )

    if args.dry_run or args.save:
        settings = build_theme_settings(selection)
        resolved = resolve_active_config_path(config_path)
        print(f"Config: {resolved}")
        for line in describe_settings(selection):
            print(f"- {line}")
        print(json.dumps(settings, indent=2, sort_keys=True))
        if args.save:
            write_config_settings(settings, resolved)
            print(f"Saved: {resolved}")
        return 0

    return run_setup_wizard(config_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

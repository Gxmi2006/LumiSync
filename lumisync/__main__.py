from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumisync",
        description="Lightweight ambient RGB synchronization engine for Windows.",
    )
    parser.add_argument("--config", help="Path to config.toml")
    parser.add_argument("--debug-overlay", action="store_true", help="Show capture/color debug overlay")
    parser.add_argument("--list-windows", action="store_true", help="List matching desktop windows and exit")
    parser.add_argument("--test-color", help="Set a single RRGGBB color and exit")
    parser.add_argument("--install-startup", action="store_true", help="Install Windows Startup shortcut and exit")
    parser.add_argument("--uninstall-startup", action="store_true", help="Remove Windows Startup shortcut and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        from lumisync.core.app import run_from_args

        return run_from_args(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


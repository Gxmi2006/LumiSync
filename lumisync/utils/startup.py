from __future__ import annotations

from pathlib import Path
import logging
import os
import sys

from lumisync.core.config import Config

LOGGER = logging.getLogger(__name__)


def startup_folder() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; cannot locate Windows Startup folder")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def install_startup_shortcut(config: Config, config_path: Path | None) -> Path:
    folder = startup_folder()
    folder.mkdir(parents=True, exist_ok=True)
    shortcut_path = folder / config.startup.shortcut_name

    try:
        import win32com.client
    except Exception as exc:
        raise RuntimeError(f"pywin32 is required to create Startup shortcut: {exc}") from exc

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = sys.executable
    args = ["-m", "lumisync"]
    if config_path is not None:
        args.extend(["--config", str(config_path)])
    shortcut.Arguments = " ".join(_quote_arg(arg) for arg in args)
    shortcut.WorkingDirectory = str(Path.cwd())
    shortcut.Description = "Lightweight ambient RGB synchronization engine for Windows"
    shortcut.Save()
    LOGGER.info("Installed Startup shortcut: %s", shortcut_path)
    return shortcut_path


def uninstall_startup_shortcut(config: Config) -> Path:
    shortcut_path = startup_folder() / config.startup.shortcut_name
    if shortcut_path.exists():
        shortcut_path.unlink()
        LOGGER.info("Removed Startup shortcut: %s", shortcut_path)
    return shortcut_path


def reconcile_startup(config: Config, config_path: Path | None) -> None:
    if config.startup.enabled:
        install_startup_shortcut(config, config_path)
    else:
        uninstall_startup_shortcut(config)


def _quote_arg(value: str) -> str:
    if not value or any(char.isspace() for char in value):
        return '"' + value.replace('"', '\\"') + '"'
    return value


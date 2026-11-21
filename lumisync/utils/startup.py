from __future__ import annotations

from pathlib import Path
import logging
import os
import shlex
import sys

from lumisync.core.config import Config
from lumisync.utils.platform_info import IS_LINUX, IS_WINDOWS

LOGGER = logging.getLogger(__name__)

LINUX_AUTOSTART_NAME = "lumisync.desktop"


def startup_folder() -> Path:
    """Folder the desktop starts programs from at login."""

    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA is not set; cannot locate Windows Startup folder")
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if IS_LINUX:
        config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        return Path(config_home) / "autostart"
    raise RuntimeError(f"Start at login is not supported on {sys.platform}")


def startup_entry_path(config: Config) -> Path:
    name = config.startup.shortcut_name if IS_WINDOWS else LINUX_AUTOSTART_NAME
    return startup_folder() / name


def _launch_args(config_path: Path | None) -> list[str]:
    # The packaged LumiSync.exe is the app itself, so it takes no "-m lumisync".
    args: list[str] = [] if getattr(sys, "frozen", False) else ["-m", "lumisync"]
    if config_path is not None:
        args.extend(["--config", str(Path(config_path).resolve())])
    return args


def install_startup_shortcut(config: Config, config_path: Path | None) -> Path:
    path = startup_entry_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    if IS_WINDOWS:
        _write_windows_shortcut(path, config_path)
    else:
        _write_linux_autostart(path, config_path)
    LOGGER.info("Installed start-at-login entry: %s", path)
    return path


def _write_windows_shortcut(path: Path, config_path: Path | None) -> None:
    try:
        import win32com.client
    except Exception as exc:
        raise RuntimeError(f"pywin32 is required to create Startup shortcut: {exc}") from exc

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(path))
    shortcut.TargetPath = sys.executable
    shortcut.Arguments = " ".join(_quote_arg(arg) for arg in _launch_args(config_path))
    shortcut.WorkingDirectory = str(Path.cwd())
    shortcut.Description = "Lightweight OpenRGB ambient lighting"
    shortcut.Save()


def _write_linux_autostart(path: Path, config_path: Path | None) -> None:
    command = " ".join(shlex.quote(part) for part in [sys.executable, *_launch_args(config_path)])
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=LumiSync\n"
        "Comment=Lightweight OpenRGB ambient lighting\n"
        f"Exec={command}\n"
        f"Path={Path.cwd()}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )


def uninstall_startup_shortcut(config: Config) -> Path:
    path = startup_entry_path(config)
    if path.exists():
        path.unlink()
        LOGGER.info("Removed start-at-login entry: %s", path)
    return path


def reconcile_startup(config: Config, config_path: Path | None) -> None:
    if config.startup.enabled:
        install_startup_shortcut(config, config_path)
    else:
        uninstall_startup_shortcut(config)


def _quote_arg(value: str) -> str:
    if not value or any(char.isspace() for char in value):
        return '"' + value.replace('"', '\\"') + '"'
    return value

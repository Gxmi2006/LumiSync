from __future__ import annotations

from logging.handlers import RotatingFileHandler
from pathlib import Path
import logging
import sys

from lumisync.core.config import app_data_dir


def setup_logging(
    level_name: str = "INFO",
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
    console_enabled: bool = True,
) -> Path:
    log_dir = app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "lumisync.log"

    level = getattr(logging, level_name.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max(50_000, int(max_bytes)),
        backupCount=max(1, int(backup_count)),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    if console_enabled:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        console.setLevel(level)
        root.addHandler(console)

    return log_path


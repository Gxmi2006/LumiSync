from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re
import shutil
import sys
from typing import Any

from lumisync.core.config import app_data_dir, ensure_default_config


SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")
KEY_RE = re.compile(r"^(\s*)([A-Za-z0-9_\-]+)(\s*=\s*)(.*)$")


def resolve_active_config_path(config_path: str | Path | None = None) -> Path:
    if config_path:
        return Path(config_path).expanduser().resolve()

    if getattr(sys, "frozen", False):
        exe_config = Path(sys.executable).resolve().parent / "config.toml"
        if exe_config.exists():
            return exe_config

    cwd_config = Path.cwd() / "config.toml"
    if cwd_config.exists():
        return cwd_config.resolve()

    if getattr(sys, "frozen", False):
        return (Path(sys.executable).resolve().parent / "config.toml").resolve()

    return (app_data_dir() / "config.toml").resolve()


def write_config_settings(
    settings: Mapping[str, Mapping[str, Any]],
    config_path: str | Path | None = None,
) -> Path:
    path = resolve_active_config_path(config_path)
    ensure_default_config(path)
    original = path.read_text(encoding="utf-8")
    updated = update_toml_text(original, settings)

    backup = path.with_suffix(path.suffix + ".bak")
    try:
        shutil.copy2(path, backup)
    except OSError:
        pass

    path.write_text(updated, encoding="utf-8")
    return path


def update_toml_text(text: str, settings: Mapping[str, Mapping[str, Any]]) -> str:
    lines = text.splitlines()
    trailing_newline = text.endswith(("\n", "\r\n"))

    current_section = ""
    found: set[tuple[str, str]] = set()
    section_ranges: dict[str, tuple[int, int]] = {}
    section_start: dict[str, int] = {}

    for index, line in enumerate(lines):
        match = SECTION_RE.match(line)
        if match:
            if current_section and current_section in section_start:
                section_ranges[current_section] = (section_start[current_section], index)
            current_section = match.group(1).strip()
            section_start[current_section] = index
            continue

        key_match = KEY_RE.match(line)
        if not key_match or current_section not in settings:
            continue

        key = key_match.group(2)
        section_settings = settings[current_section]
        if key not in section_settings:
            continue

        prefix, _key, separator, value_part = key_match.groups()
        value, comment = _split_comment(value_part)
        _ = value
        lines[index] = f"{prefix}{key}{separator}{_format_value(section_settings[key])}{comment}"
        found.add((current_section, key))

    if current_section and current_section in section_start:
        section_ranges[current_section] = (section_start[current_section], len(lines))

    for section, values in settings.items():
        missing = [(key, value) for key, value in values.items() if (section, key) not in found]
        if not missing:
            continue

        if section not in section_ranges:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(f"[{section}]")
            section_ranges[section] = (len(lines) - 1, len(lines))

        start, end = section_ranges[section]
        insert_at = end
        additions = [f"{key} = {_format_value(value)}" for key, value in missing]
        lines[insert_at:insert_at] = additions

        added = len(additions)
        for name, (range_start, range_end) in list(section_ranges.items()):
            if range_start >= insert_at:
                section_ranges[name] = (range_start + added, range_end + added)
            elif range_end >= insert_at:
                section_ranges[name] = (range_start, range_end + added)
        section_ranges[section] = (start, end + added)

    result = "\n".join(lines)
    if trailing_newline or not result.endswith("\n"):
        result += "\n"
    return result


def _split_comment(value: str) -> tuple[str, str]:
    in_string = False
    escaped = False
    for index, char in enumerate(value):
        if char == "\\" and in_string:
            escaped = not escaped
            continue
        if char == '"' and not escaped:
            in_string = not in_string
        if char == "#" and not in_string:
            before = value[:index].rstrip()
            after = value[index:]
            spacing = " " if before else ""
            return before, f"{spacing}{after}"
        escaped = False
    return value.strip(), ""


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_format_value(entry) for entry in value) + "]"
    return _format_value(str(value))

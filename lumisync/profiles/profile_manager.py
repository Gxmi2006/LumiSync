from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    values: dict[str, Any]


class ProfileManager:
    """Load named TOML profiles without mutating the active Config object."""

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def load_profiles(self) -> dict[str, Profile]:
        with self.config_path.open("rb") as handle:
            data = tomllib.load(handle)
        raw_profiles = data.get("profiles", {})
        if not isinstance(raw_profiles, dict):
            return {}
        return {
            name: Profile(name=name, values=values)
            for name, values in raw_profiles.items()
            if isinstance(values, dict)
        }

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import socket
import sys

from lumisync.backends.backend_manager import BackendStatusReport
from lumisync.core.config import Config, ConfigIssue


@dataclass(frozen=True, slots=True)
class CheckItem:
    name: str
    ok: bool
    detail: str
    fix: str = ""

    def line(self) -> str:
        icon = "OK" if self.ok else "FAIL"
        suffix = f" Fix: {self.fix}" if self.fix and not self.ok else ""
        return f"- [{icon}] {self.name}: {self.detail}{suffix}"


class SetupCheckReport:
    def __init__(
        self,
        config: Config,
        config_path: Path | None,
        config_issues: tuple[ConfigIssue, ...],
        backend_report: BackendStatusReport | None,
    ) -> None:
        self.config = config
        self.config_path = config_path
        self.config_issues = config_issues
        self.backend_report = backend_report

    def to_markdown(self) -> str:
        checks = self._checks()
        lines = [
            "# LumiSync Setup Check",
            "",
            f"- Config path: {self.config_path or 'auto-detected config.toml'}",
            f"- OpenRGB target: {self.config.openrgb.address}:{self.config.openrgb.port}",
            f"- Controller preference: {self.config.app.controller}",
            "",
            "## Checks",
            *[item.line() for item in checks],
        ]
        if self.config_issues:
            lines.extend(["", "## Config Warnings"])
            lines.extend(f"- {issue.line()}" for issue in self.config_issues)
        if self.backend_report:
            lines.extend(["", "## Backend Probe"])
            lines.extend(f"- {line.strip()}" for line in self.backend_report.lines()[1:])
        failing = [item for item in checks if not item.ok]
        lines.extend(["", "## Next Steps"])
        if failing:
            lines.extend(f"- {item.fix}" for item in failing if item.fix)
        else:
            lines.append("- Setup looks ready. Run `python -m lumisync --diagnostics`, then start LumiSync normally.")
        return "\n".join(lines)

    def _checks(self) -> list[CheckItem]:
        checks = [
            self._python_check(),
            *self._dependency_checks(),
            self._openrgb_socket_check(),
            self._backend_check(),
            self._hotkey_check(),
        ]
        checks.append(
            CheckItem(
                "Config",
                not self.config_issues,
                "valid" if not self.config_issues else f"{len(self.config_issues)} warning(s); safe values were applied",
                "Open config.toml and fix the warnings listed below.",
            )
        )
        return checks

    @staticmethod
    def _python_check() -> CheckItem:
        version = sys.version_info
        ok = version >= (3, 10)
        return CheckItem(
            "Python",
            ok,
            f"{version.major}.{version.minor}.{version.micro}",
            "Install Python 3.10 or newer from python.org.",
        )

    @staticmethod
    def _dependency_checks() -> list[CheckItem]:
        modules = {
            "cv2": "opencv-python",
            "keyboard": "keyboard",
            "mss": "mss",
            "numpy": "numpy",
            "openrgb": "openrgb-python",
            "PIL": "pillow",
            "psutil": "psutil",
            "pystray": "pystray",
            "win32gui": "pywin32",
        }
        checks: list[CheckItem] = []
        missing: list[str] = []
        for module, package in modules.items():
            ok = importlib.util.find_spec(module) is not None
            if not ok:
                missing.append(package)
            checks.append(
                CheckItem(
                    f"Dependency {package}",
                    ok,
                    "installed" if ok else f"module {module!r} not importable",
                    "Run `pip install -r requirements.txt`.",
                )
            )
        if missing:
            checks.append(
                CheckItem(
                    "Dependency summary",
                    False,
                    ", ".join(sorted(set(missing))),
                    "Activate your venv, then run `pip install -r requirements.txt`.",
                )
            )
        return checks

    def _openrgb_socket_check(self) -> CheckItem:
        try:
            with socket.create_connection(
                (self.config.openrgb.address, self.config.openrgb.port),
                timeout=max(0.1, self.config.openrgb.socket_timeout_seconds),
            ):
                return CheckItem("OpenRGB SDK Server", True, "listening")
        except OSError as exc:
            return CheckItem(
                "OpenRGB SDK Server",
                False,
                str(exc),
                "Open OpenRGB, go to SDK Server, click Start Server, and keep port 6742 unless changed.",
            )

    def _backend_check(self) -> CheckItem:
        if self.backend_report is None:
            return CheckItem("RGB backend", False, "not probed", "Run `python -m lumisync --diagnostics`.")
        active = self.backend_report.active_backend
        ok = active not in {"software fallback", "none"}
        if ok:
            return CheckItem("RGB backend", True, f"active backend is {active}")
        return CheckItem(
            "RGB backend",
            False,
            f"active backend is {active}",
            "Fix OpenRGB SDK Server or device detection; LumiSync will still run in software fallback.",
        )

    @staticmethod
    def _hotkey_check() -> CheckItem:
        try:
            import keyboard  # noqa: F401
        except Exception as exc:
            return CheckItem(
                "Global hotkeys",
                False,
                str(exc),
                "Install the `keyboard` package. On some systems, run LumiSync as administrator.",
            )
        return CheckItem(
            "Global hotkeys",
            True,
            "keyboard package available; administrator permission may still be required on some PCs",
        )

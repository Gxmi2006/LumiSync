from __future__ import annotations

from dataclasses import dataclass
import platform
import sys

from lumisync.backends.backend_manager import BackendStatusReport
from lumisync.capture.monitor_detection import list_monitors
from lumisync.core.config import Config


@dataclass(frozen=True, slots=True)
class DiagnosticsReport:
    config: Config
    backend_report: BackendStatusReport | None = None

    def to_markdown(self) -> str:
        lines = [
            "# LumiSync Diagnostics",
            "",
            f"- OS: {platform.platform()}",
            f"- Python: {sys.version.split()[0]}",
            f"- Capture mode: {self.config.app.capture_mode}",
            f"- FPS target: {self.config.app.fps}",
            f"- Visual priority: {'enabled' if self.config.visual_priority.enabled else 'disabled'}",
            f"- RGB controller preference: {self.config.app.controller}",
            "",
            "## Backend Status",
        ]
        if self.backend_report:
            lines.extend(f"- {line.strip()}" for line in self.backend_report.lines()[1:])
        else:
            lines.append("- Not probed yet")
        if self.config.diagnostics.include_monitor_report:
            lines.extend(["", "## Monitors"])
            try:
                for monitor in list_monitors():
                    rect = monitor.rect
                    lines.append(
                        f"- {monitor.label}: x={rect.left}, y={rect.top}, "
                        f"{rect.width}x{rect.height}"
                    )
            except Exception as exc:
                lines.append(f"- Monitor detection failed: {exc}")
        return "\n".join(lines)

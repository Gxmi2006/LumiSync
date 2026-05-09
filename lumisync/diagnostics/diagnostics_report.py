from __future__ import annotations

from dataclasses import dataclass
import platform
import sys

from lumisync.backends.backend_manager import BackendStatusReport
from lumisync.capture.monitor_detection import list_monitors
from lumisync.capture.region_capture import compute_capture_region, compute_region_from_rect
from lumisync.capture.window_capture import WindowFinder
from lumisync.core.config import Config, ConfigIssue


@dataclass(frozen=True, slots=True)
class DiagnosticsReport:
    config: Config
    backend_report: BackendStatusReport | None = None
    config_issues: tuple[ConfigIssue, ...] = ()

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
            f"- Software fallback active: {self._fallback_active()}",
            "",
            "## Backend Status",
        ]
        if self.backend_report:
            lines.extend(f"- {line.strip()}" for line in self.backend_report.lines()[1:])
        else:
            lines.append("- Not probed yet")
        lines.extend(["", "## Capture Target"])
        lines.extend(self._capture_target_lines())
        if self.config_issues:
            lines.extend(["", "## Config Warnings"])
            lines.extend(f"- {issue.line()}" for issue in self.config_issues)
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
        lines.extend(["", "## Suggested Fixes"])
        lines.extend(self._suggestion_lines())
        return "\n".join(lines)

    def _fallback_active(self) -> str:
        if not self.backend_report:
            return "unknown"
        return "yes" if self.backend_report.active_backend in {"software fallback", "none"} else "no"

    def _capture_target_lines(self) -> list[str]:
        mode = self.config.app.capture_mode.lower()
        lines = [f"- Mode: {mode}"]
        try:
            if mode in {"monitor", "region"}:
                monitors = list_monitors()
                if mode == "region":
                    selected = next((item for item in monitors if item.is_virtual_desktop), monitors[0] if monitors else None)
                else:
                    selected = next((item for item in monitors if item.index == self.config.monitor.index), None)
                if selected is None:
                    return [*lines, "- Selected target: none"]
                region = compute_region_from_rect(selected.rect, self.config.capture)
                rect = selected.rect
                lines.append(f"- Selected target: {selected.label} ({rect.left},{rect.top} {rect.width}x{rect.height})")
                if region is not None:
                    lines.append(f"- Capture region: {region.left},{region.top} {region.width}x{region.height}")
                else:
                    lines.append("- Capture region: invalid after applying crop settings")
                return lines

            finder = WindowFinder(self.config.window)
            window = finder.get_window()
            if window is None:
                return [*lines, "- Selected target: no matching visible window"]
            rect = window.client_rect
            lines.append(
                f"- Selected target: hwnd={window.hwnd} pid={window.pid} "
                f"process={window.process_name!r} title={window.title!r}"
            )
            lines.append(f"- Window state: {'minimized' if window.minimized else 'visible'}")
            lines.append(f"- Client rect: {rect.left},{rect.top} {rect.width}x{rect.height}")
            region = compute_capture_region(window, self.config.capture)
            if region is not None:
                lines.append(f"- Capture region: {region.left},{region.top} {region.width}x{region.height}")
            else:
                lines.append("- Capture region: invalid after applying crop settings")
            return lines
        except Exception as exc:
            return [*lines, f"- Target detection failed: {exc}"]

    def _suggestion_lines(self) -> list[str]:
        suggestions: list[str] = []
        if self.backend_report:
            openrgb = self.backend_report.openrgb
            if openrgb.status in {"not running", "timeout"}:
                suggestions.append("- OpenRGB: open OpenRGB, go to SDK Server, click Start Server, then rerun diagnostics.")
            elif openrgb.status == "no devices":
                suggestions.append("- OpenRGB: rescan devices in OpenRGB and confirm your keyboard/device appears there first.")
            elif openrgb.status == "not found":
                suggestions.append("- OpenRGB: install dependencies with `pip install -r requirements.txt`.")
            if self.backend_report.active_backend in {"software fallback", "none"}:
                suggestions.append("- RGB output: LumiSync is running safely, but no hardware backend is active.")
        if self.config.app.capture_mode in {"active_window", "window"}:
            suggestions.append("- Capture: use `--list-windows` to verify the target window, or tune `[window]` in config.toml.")
        if self.config_issues:
            suggestions.append("- Config: warnings above were clamped to safe values; edit config.toml to remove them permanently.")
        if not suggestions:
            suggestions.append("- No immediate fixes suggested. Diagnostics look healthy.")
        return suggestions

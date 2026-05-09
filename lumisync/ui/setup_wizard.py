from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from lumisync.core.config_writer import resolve_active_config_path, write_config_settings
from lumisync.core.theme_presets import (
    CONTENT_CHOICES,
    DEVICE_CHOICES,
    INTENSITY_CHOICES,
    MOOD_CHOICES,
    MULTICOLOR_CHOICES,
    Choice,
    ThemeSelection,
    build_theme_settings,
    describe_settings,
)


class SetupWizard:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = resolve_active_config_path(config_path)
        self.root = tk.Tk()
        self.root.title("LumiSync Setup")
        self.root.geometry("720x620")
        self.root.minsize(640, 560)
        self.root.configure(bg="#111418")

        self.mood = tk.StringVar(value="cinematic")
        self.multicolor = tk.StringVar(value="elegant")
        self.content = tk.StringVar(value="movies")
        self.intensity = tk.StringVar(value="subtle")
        self.device_preference = tk.StringVar(value="keyboard")
        self.status = tk.StringVar(value=f"Config: {self.config_path}")

        self._configure_style()
        self._build()

    def run(self) -> int:
        self.root.mainloop()
        return 0

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#111418")
        style.configure("Card.TFrame", background="#1A1F26", relief="flat")
        style.configure("TLabel", background="#111418", foreground="#E5E7EB", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#111418", foreground="#F9FAFB", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background="#111418", foreground="#AAB2C0", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#1A1F26", foreground="#F9FAFB", font=("Segoe UI", 11, "bold"))
        style.configure("CardText.TLabel", background="#1A1F26", foreground="#B7C0CE", font=("Segoe UI", 9))
        style.configure("TRadiobutton", background="#1A1F26", foreground="#E5E7EB", font=("Segoe UI", 9))
        style.map("TRadiobutton", background=[("active", "#202733")], foreground=[("active", "#FFFFFF")])
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="LumiSync Setup", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Choose an RGB feel. LumiSync will update config.toml and keep OpenRGB as the hardware path.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 16))

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        self._radio_card(content, "What mood do you want?", MOOD_CHOICES, self.mood, 0, 0)
        self._radio_card(content, "Do you want multiple colors?", MULTICOLOR_CHOICES, self.multicolor, 0, 1)
        self._radio_card(content, "What do you mostly watch/play?", CONTENT_CHOICES, self.content, 1, 0)
        self._radio_card(content, "How intense should it feel?", INTENSITY_CHOICES, self.intensity, 1, 1)
        self._radio_card(content, "OpenRGB device preference", DEVICE_CHOICES, self.device_preference, 2, 0, columnspan=2)

        summary_frame = ttk.Frame(outer, style="Card.TFrame", padding=14)
        summary_frame.pack(fill="x", pady=(14, 10))
        ttk.Label(summary_frame, text="Preview", style="CardTitle.TLabel").pack(anchor="w")
        self.preview = tk.Text(
            summary_frame,
            height=5,
            bg="#101419",
            fg="#DCE4F0",
            insertbackground="#DCE4F0",
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
        )
        self.preview.pack(fill="x", pady=(8, 0))
        self.preview.configure(state="disabled")

        for variable in (
            self.mood,
            self.multicolor,
            self.content,
            self.intensity,
            self.device_preference,
        ):
            variable.trace_add("write", lambda *_: self._refresh_preview())
        self._refresh_preview()

        ttk.Label(outer, textvariable=self.status, style="Subtitle.TLabel").pack(anchor="w", pady=(0, 8))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Save Settings", style="Accent.TButton", command=self._save).pack(side="left")
        ttk.Button(buttons, text="Launch LumiSync", command=self._launch).pack(side="left", padx=(10, 0))
        ttk.Button(buttons, text="Close", command=self.root.destroy).pack(side="right")

    def _radio_card(
        self,
        parent: ttk.Frame,
        title: str,
        choices: tuple[Choice, ...],
        variable: tk.StringVar,
        row: int,
        column: int,
        columnspan: int = 1,
    ) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=14)
        frame.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=6, pady=6)
        ttk.Label(frame, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(0, 6))
        for choice in choices:
            button = ttk.Radiobutton(
                frame,
                text=choice.label,
                value=choice.key,
                variable=variable,
            )
            button.pack(anchor="w", pady=(4, 0))
            ttk.Label(frame, text=choice.description, style="CardText.TLabel", wraplength=300).pack(
                anchor="w",
                padx=(24, 0),
            )

    def _selection(self) -> ThemeSelection:
        return ThemeSelection(
            mood=self.mood.get(),
            multicolor=self.multicolor.get(),
            content=self.content.get(),
            intensity=self.intensity.get(),
            device_preference=self.device_preference.get(),
        )

    def _refresh_preview(self) -> None:
        lines = describe_settings(self._selection())
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", "\n".join(lines))
        self.preview.configure(state="disabled")

    def _save(self) -> bool:
        try:
            path = write_config_settings(build_theme_settings(self._selection()), self.config_path)
        except Exception as exc:
            messagebox.showerror("LumiSync Setup", f"Could not save settings:\n{exc}")
            return False
        self.status.set(f"Saved settings to {path}")
        messagebox.showinfo("LumiSync Setup", f"Settings saved to:\n{path}")
        return True

    def _launch(self) -> None:
        if not self._save():
            return
        try:
            subprocess.Popen(_launch_command(self.config_path), cwd=str(self.config_path.parent))
        except Exception as exc:
            messagebox.showerror("LumiSync Setup", f"Could not launch LumiSync:\n{exc}")
            return
        self.status.set("LumiSync launched.")


def run_setup_wizard(config_path: Path | None = None) -> int:
    return SetupWizard(config_path).run()


def _launch_command(config_path: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve().parent / "LumiSync.exe"
        if exe.exists():
            return [str(exe)]
    return [sys.executable, "-m", "lumisync", "--config", str(config_path)]

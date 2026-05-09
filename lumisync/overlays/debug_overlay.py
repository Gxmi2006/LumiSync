from __future__ import annotations

from dataclasses import dataclass
import logging
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any
import tkinter as tk

from lumisync.core.color import RGB
from lumisync.capture.window_capture import Rect

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OverlayData:
    region: Rect
    color: RGB
    fps: float
    status: str
    controller: str
    visual_debug: Any = None


class DebugOverlay:
    def __init__(self) -> None:
        self._queue: Queue[OverlayData | None] = Queue(maxsize=4)
        self._stop = Event()
        self._thread: Thread | None = None
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            self._enabled = True
            return
        self._stop.clear()
        self._enabled = True
        self._thread = Thread(target=self._run, name="DebugOverlay", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._enabled = False
        self._stop.set()
        self._put(None)

    def toggle(self) -> bool:
        if self._enabled:
            self.stop()
            return False
        self.start()
        return True

    def update(self, data: OverlayData) -> None:
        if not self._enabled:
            return
        self._put(data)

    def _put(self, data: OverlayData | None) -> None:
        try:
            while self._queue.full():
                self._queue.get_nowait()
            self._queue.put_nowait(data)
        except Exception:
            pass

    def _run(self) -> None:
        try:
            root = tk.Tk()
        except Exception as exc:
            LOGGER.warning("Debug overlay unavailable: %s", exc)
            self._enabled = False
            return

        transparent = "#ff00ff"
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        try:
            root.wm_attributes("-transparentcolor", transparent)
        except tk.TclError:
            root.wm_attributes("-alpha", 0.75)
        root.configure(bg=transparent)

        canvas = tk.Canvas(root, bg=transparent, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)

        def poll() -> None:
            if self._stop.is_set():
                root.destroy()
                return
            try:
                while True:
                    item = self._queue.get_nowait()
                    if item is None:
                        root.destroy()
                        return
                    self._draw(root, canvas, item, transparent)
            except Empty:
                pass
            root.after(33, poll)

        root.after(0, poll)
        try:
            root.mainloop()
        finally:
            self._enabled = False

    @staticmethod
    def _draw(root: tk.Tk, canvas: tk.Canvas, data: OverlayData, transparent: str) -> None:
        region = data.region
        root.geometry(f"{region.width}x{region.height}+{region.left}+{region.top}")
        canvas.config(width=region.width, height=region.height, bg=transparent)
        canvas.delete("all")
        color_hex = data.color.to_hex()
        canvas.create_rectangle(
            1,
            1,
            region.width - 2,
            region.height - 2,
            outline=color_hex,
            width=3,
        )
        label = f"{color_hex}  {data.fps:4.1f} FPS  {data.controller}  {data.status}"
        text_width = min(region.width - 12, max(260, len(label) * 7))
        canvas.create_rectangle(6, 6, text_width, 34, fill="#101010", outline=color_hex)
        canvas.create_rectangle(12, 12, 28, 28, fill=color_hex, outline="")
        canvas.create_text(
            36,
            20,
            anchor="w",
            text=label,
            fill="#ffffff",
            font=("Segoe UI", 9),
        )
        DebugOverlay._draw_visual_debug(canvas, data)

    @staticmethod
    def _draw_visual_debug(canvas: tk.Canvas, data: OverlayData) -> None:
        debug = data.visual_debug
        if debug is None:
            return

        region = data.region
        boxes = getattr(debug, "region_boxes", ()) or ()
        selected = getattr(debug, "selected_bbox", None)

        for idx, box in enumerate(boxes[:8]):
            x, y, w, h, score = box
            left = int(x * region.width)
            top = int(y * region.height)
            right = int((x + w) * region.width)
            bottom = int((y + h) * region.height)
            outline = "#FFFFFF" if idx == 0 else "#22D3EE"
            width_px = 3 if idx == 0 else 2
            canvas.create_rectangle(left, top, right, bottom, outline=outline, width=width_px)
            canvas.create_rectangle(left, max(36, top - 18), left + 74, max(54, top), fill="#101010", outline=outline)
            canvas.create_text(
                left + 5,
                max(45, top - 9),
                anchor="w",
                text=f"VP {score:.2f}",
                fill="#ffffff",
                font=("Segoe UI", 8),
            )

        if selected is not None:
            x, y, w, h = selected
            canvas.create_rectangle(
                int(x * region.width),
                int(y * region.height),
                int((x + w) * region.width),
                int((y + h) * region.height),
                outline="#FB7185",
                width=1,
                dash=(4, 3),
            )

        palette = getattr(debug, "palette", ()) or ()
        if palette:
            swatch = 18
            x0 = 8
            y0 = region.height - swatch - 8
            for idx, color in enumerate(palette[:6]):
                x = x0 + idx * (swatch + 5)
                canvas.create_rectangle(
                    x,
                    y0,
                    x + swatch,
                    y0 + swatch,
                    fill=color.to_hex(),
                    outline="#101010",
                )

        saliency_grid = getattr(debug, "saliency_grid", ()) or ()
        if saliency_grid:
            grid_w = len(saliency_grid[0]) if saliency_grid[0] else 0
            grid_h = len(saliency_grid)
            if grid_w and grid_h:
                cell = 4
                x0 = max(8, region.width - grid_w * cell - 8)
                y0 = 42
                for row_idx, row in enumerate(saliency_grid):
                    for col_idx, value in enumerate(row):
                        if value < 12:
                            continue
                        color = _heat_color(value)
                        canvas.create_rectangle(
                            x0 + col_idx * cell,
                            y0 + row_idx * cell,
                            x0 + (col_idx + 1) * cell,
                            y0 + (row_idx + 1) * cell,
                            fill=color,
                            outline="",
                        )


def _heat_color(value: int) -> str:
    value = max(0, min(255, int(value)))
    if value < 96:
        return f"#{0:02X}{value + 64:02X}{255:02X}"
    if value < 180:
        red = int((value - 96) / 84 * 255)
        return f"#{red:02X}{255:02X}{120:02X}"
    green = max(0, 255 - int((value - 180) / 75 * 180))
    return f"#{255:02X}{green:02X}{80:02X}"


from __future__ import annotations

from dataclasses import dataclass
import logging
from queue import Empty, Queue
from threading import Event, Thread
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


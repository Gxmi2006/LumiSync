from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class WebSocketStatusServer:
    """Optional local status/control websocket server.

    The server is intentionally dependency-optional. Install `websockets` and
    wire this into the app loop when the API graduates from roadmap to runtime.
    """

    host: str = "127.0.0.1"
    port: int = 8765
    _clients: set[Any] = field(default_factory=set)
    _server: Any = None

    async def start(self) -> None:
        try:
            import websockets
        except Exception as exc:
            raise RuntimeError("Install the optional 'websockets' package to enable the API") from exc

        self._server = await websockets.serve(self._handler, self.host, self.port)
        LOGGER.info("LumiSync websocket API listening on ws://%s:%s", self.host, self.port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self._clients:
            return
        message = json.dumps(payload, separators=(",", ":"))
        await asyncio.gather(
            *(client.send(message) for client in tuple(self._clients)),
            return_exceptions=True,
        )

    async def _handler(self, websocket: Any) -> None:
        self._clients.add(websocket)
        try:
            async for _message in websocket:
                await websocket.send(json.dumps({"ok": True, "app": "LumiSync"}))
        finally:
            self._clients.discard(websocket)

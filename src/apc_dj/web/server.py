"""Kleiner Webserver: liefert die Oberfläche aus und spricht per WebSocket mit der App."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from ..app import App

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"


def create_server(core: App) -> FastAPI:
    api = FastAPI(title="DJ-Schule")

    @api.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        # Nur die eigene Oberfläche darf sich verbinden – keine fremden Webseiten
        # (Schutz vor Cross-Site WebSocket Hijacking).
        origin = websocket.headers.get("origin")
        if origin is not None and urlparse(origin).netloc != websocket.headers.get("host"):
            log.warning("WebSocket von fremder Herkunft abgelehnt: %s", origin)
            await websocket.close(code=1008)
            return
        await websocket.accept()
        loop = asyncio.get_running_loop()
        queue = core.bus.subscribe(loop)
        await websocket.send_json(core.state())

        async def sender() -> None:
            while True:
                await websocket.send_json(await queue.get())

        task = asyncio.create_task(sender())
        try:
            while True:
                try:
                    data = await websocket.receive_json()
                except ValueError:
                    continue  # kein gültiges JSON
                try:
                    core.handle_web(data)
                except Exception:  # noqa: BLE001
                    log.exception("Ungültige Nachricht vom Browser: %s", data)
        except WebSocketDisconnect:
            pass
        finally:
            task.cancel()
            core.bus.unsubscribe(queue)

    api.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return api

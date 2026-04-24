from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from treehouse.server.state import StateManager


def create_app(state: StateManager) -> FastAPI:
    app = FastAPI(title="Treehouse API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    connected: list[WebSocket] = []

    async def broadcast(message: str):
        for ws in connected[:]:
            try:
                await ws.send_text(message)
            except Exception:
                connected.remove(ws)

    # Wire state callbacks to broadcast
    def on_log(msg: str):
        asyncio.create_task(broadcast(msg))

    def on_status(msg: str):
        asyncio.create_task(broadcast(msg))

    state.on_log = on_log
    state.on_status_change = on_status

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/agents")
    async def get_agents():
        return json.loads(state.snapshot())

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        connected.append(websocket)

        # Send initial state
        await websocket.send_text(state.snapshot())

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")
                if msg_type == "spawn":
                    # Handled by CLI/TUI -- web dashboard sends command,
                    # server acknowledges. Full spawn logic stays in core.
                    await websocket.send_text(
                        json.dumps({"type": "ack", "action": "spawn", "name": msg.get("name")})
                    )
                elif msg_type == "stop":
                    await websocket.send_text(
                        json.dumps({"type": "ack", "action": "stop", "name": msg.get("name")})
                    )
                elif msg_type == "merge":
                    await websocket.send_text(
                        json.dumps({"type": "ack", "action": "merge", "name": msg.get("name")})
                    )
        except WebSocketDisconnect:
            connected.remove(websocket)

    # Background task to broadcast state every second
    @app.on_event("startup")
    async def start_broadcaster():
        async def tick():
            while True:
                await asyncio.sleep(1.0)
                if connected:
                    await broadcast(state.snapshot())
        asyncio.create_task(tick())

    return app

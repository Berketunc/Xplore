"""Bounded mouse-interaction sessions; provider credentials remain server-side."""

import asyncio
import logging
from pathlib import Path
import secrets
import time

import modal
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from backend.geometry import InteractiveConfig, build_geometry
from backend.interactive import validate_command


SessionRequest = InteractiveConfig


def install_interactive_routes(app, *, claims, volume, stream_function):
    @app.get("/sandbox")
    def sandbox():
        return FileResponse(Path(__file__).parent / "static/sandbox.html")

    @app.get("/v1/interactive/mesh")
    def mesh():
        return build_geometry().mesh

    @app.post("/v1/interactive/preview")
    def preview(body: SessionRequest):
        return build_geometry(body.resolved()).mesh

    @app.post("/v1/interactive/sessions", status_code=201)
    def session(body: SessionRequest):
        active = claims.get("interactive-active")
        if active and active["expires"] > time.time():
            raise HTTPException(409, "The live worker is busy; try again when the current session ends")
        identifier = secrets.token_hex(16)
        for slot in range(20):
            if claims.put(f"interactive-credit-v1-{slot}", identifier, skip_if_exists=True):
                value = {"candidate_id": body.candidate_id, "configuration": body.resolved(), "created_at": time.time(), "expires": time.time()+180}
                claims.put("interactive-session:"+identifier, value)
                return {"session_id": identifier, "websocket_url": f"/v1/interactive/sessions/{identifier}/stream",
                    "max_live_seconds": 90, "remaining_starts": 19-slot, "configuration": body.resolved(),
                    "notice": "Exploratory live MPM physics; the browser surface is an approximate visualization."}
        raise HTTPException(429, "The demo's bounded live-session allowance has been used")

    @app.websocket("/v1/interactive/sessions/{identifier}/stream")
    async def stream(websocket: WebSocket, identifier: str):
        value = await claims.get.aio("interactive-session:"+identifier)
        if value is None or value["expires"] < time.time():
            await websocket.close(code=1008)
            return
        active = await claims.get.aio("interactive-active")
        if active and active["expires"] < time.time():
            await claims.pop.aio("interactive-active", None)
        acquired = await claims.put.aio("interactive-active", {"id": identifier, "expires": time.time()+185}, skip_if_exists=True)
        joined = await claims.put.aio("interactive-joined:"+identifier, True, skip_if_exists=True) if acquired else False
        if not acquired or not joined:
            if acquired:
                await claims.pop.aio("interactive-active", None)
            await websocket.close(code=1013)
            return
        await websocket.accept()
        await websocket.send_json({"type": "loading", "message": "Starting GPU physics. The first session can take about a minute while a GPU starts and kernels compile."})
        try:
            async with modal.Queue.ephemeral() as commands:
                ready = asyncio.Event()
                async def receive():
                    last_move = 0.
                    while True:
                        message = validate_command(await websocket.receive_json())
                        if message["type"] == "move" and time.monotonic()-last_move < .025:
                            continue
                        if message["type"] == "move":
                            last_move = time.monotonic()
                        await commands.put.aio(message)
                        if message["type"] == "stop":
                            return

                async def send():
                    try:
                        async for packet in stream_function.remote_gen.aio(commands, value["candidate_id"], value.get("configuration")):
                            if packet["type"] == "ready":
                                ready.set()
                            await websocket.send_json(packet)
                    except Exception:
                        logging.exception("Interactive physics stream stopped")
                        await websocket.send_json({"type": "error", "message": "The physics worker stopped. Start another session to reset it."})

                async def startup_deadline():
                    try:
                        await asyncio.wait_for(ready.wait(), timeout=100)
                        await asyncio.Future()
                    except asyncio.TimeoutError:
                        await websocket.send_json({"type": "error", "message": "A GPU could not start in time. Try another session shortly."})

                receiver = asyncio.create_task(receive())
                sender = asyncio.create_task(send())
                deadline = asyncio.create_task(startup_deadline())
                try:
                    done, _ = await asyncio.wait([receiver, sender, deadline], return_when=asyncio.FIRST_COMPLETED)
                    if receiver in done and isinstance(receiver.exception(), ValueError):
                        await websocket.send_json({"type": "error", "message": "The interaction command was invalid. Start another session."})
                finally:
                    await commands.put.aio({"type": "stop"})
                    receiver.cancel()
                    sender.cancel()
                    deadline.cancel()
                    await asyncio.gather(receiver, sender, deadline, return_exceptions=True)
        except (WebSocketDisconnect, RuntimeError, ValueError):
            pass
        finally:
            active = await claims.get.aio("interactive-active")
            if active and active["id"] == identifier:
                await claims.pop.aio("interactive-active", None)
            try:
                await websocket.close()
            except RuntimeError:
                pass

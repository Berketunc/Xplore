"""Test real GPU deformation through the public mouse-session protocol."""

import argparse
import json
import math
from pathlib import Path
import time

import httpx
from websockets.sync.client import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--candidate", choices=("flexible", "balanced", "firm"), default="balanced")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=30) as client:
        assert client.get("/sandbox").status_code == 200
        mesh = client.get("/v1/interactive/mesh").json()
        assert len(mesh["triangles"]) > 0
        created = client.post("/v1/interactive/sessions", json={"candidate_id": args.candidate})
        assert created.status_code == 201, created.text
        session = created.json()
    url = base.replace("https://", "wss://").replace("http://", "ws://") + session["websocket_url"]
    connected = time.monotonic()
    with connect(url, open_timeout=30, max_size=2**21, compression=None) as socket:
        while True:
            packet = json.loads(socket.recv(timeout=160))
            if packet["type"] == "error":
                raise RuntimeError(packet["message"])
            if packet["type"] == "ready":
                initial = packet["mesh"]["positions"]
                ready_seconds = time.monotonic()-connected
                break
        count = len(initial)//3
        index = max(range(count), key=lambda i: initial[i*3+2])
        point = initial[index*3:index*3+3]
        target = point.copy()
        target[2] -= .12
        socket.send(json.dumps({"type": "grab", "point": point, "target": target}))
        sent = time.monotonic()
        max_displacement = 0.
        first_motion = None
        samples = 0
        received = []
        while time.monotonic()-sent < 6:
            packet = json.loads(socket.recv(timeout=15))
            if packet["type"] != "frame":
                continue
            positions = packet["positions"]
            assert len(positions) == len(initial) and all(math.isfinite(v) for v in positions)
            displacements = [math.dist(initial[i*3:i*3+3],positions[i*3:i*3+3]) for i in range(count)]
            maximum = max(displacements)
            max_displacement = max(max_displacement, maximum)
            received.append(time.monotonic())
            samples += 1
            if maximum > .001 and first_motion is None:
                first_motion = time.monotonic()-sent
            if samples >= 40 and maximum > .03:
                break
        assert max_displacement > .005, f"Grab did not deform the object: {max_displacement}"
        assert max(displacements)-min(displacements) > .005, "The update only translated the object rigidly"
        socket.send(json.dumps({"type": "release"}))
        for _ in range(5):
            assert json.loads(socket.recv(timeout=15))["type"] == "frame"
        socket.send(json.dumps({"type": "reset"}))
        reset_ok = False
        for _ in range(100):
            packet = json.loads(socket.recv(timeout=15))
            if packet["type"] == "frame" and max(abs(a-b) for a,b in zip(packet["positions"],initial)) < .002:
                reset_ok = True
                break
        assert reset_ok, "Reset did not restore the reference object"
        socket.send(json.dumps({"type": "stop"}))
    fps = (len(received)-1)/(received[-1]-received[0]) if len(received)>1 else 0.
    result = {"base_url": base, "candidate_id": args.candidate, "session_id": session["session_id"], "ready_seconds": ready_seconds,
        "received_updates_per_second": fps, "first_motion_seconds": first_motion,
        "max_surface_displacement_mpm": max_displacement, "reset_verified": reset_ok,
        "surface_vertices": count, "physics": "PowerSim bundled MPM; browser display uses a convex surface proxy",
        "checks": ["public WebSocket", "real GPU grab deformation", "non-rigid motion", "finite positions", "release", "reset", "stop"]}
    suffix = "" if args.candidate == "balanced" else "-"+args.candidate
    Path(f"docs/interactive-verification{suffix}.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()

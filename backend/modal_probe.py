"""Bounded GPU access check: modal run backend/modal_probe.py.

This probe deliberately needs no checkpoints or simulation dependencies.
"""

import json

import modal

app = modal.App("xplore-feasibility")
probe_image = modal.Image.debian_slim(python_version="3.11")


@app.function(
    image=probe_image,
    gpu="L40S",
    cpu=1,
    memory=1024,
    timeout=60,
    max_containers=1,
    scaledown_window=2,
    retries=0,
)
def gpu_probe():
    import subprocess
    import time

    started = time.monotonic()
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return {"gpu": result.stdout.strip(), "probe_seconds": time.monotonic() - started}


@app.local_entrypoint()
def main():
    print(json.dumps(gpu_probe.remote(), indent=2))

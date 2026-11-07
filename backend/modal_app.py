"""PowerSim feasibility worker on Modal.

    modal run backend/modal_app.py --stage prepare
    modal run backend/modal_app.py --stage baseline

Only the chosen pillow checkpoint is downloaded. Jobs are serial and bounded.
"""

from pathlib import Path

import modal

UPSTREAM_COMMIT = "24266e5264a213bceb426796ce91e12a555e2f69"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".cache" / "PowerSim"
SCENE = "pillow2sofa_gs_fewer_points"
app = modal.App("xplore-simulation")
volume = modal.Volume.from_name("xplore-experiments", create_if_missing=True)
inspection_image = modal.Image.debian_slim(python_version="3.11")

runtime_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libgl1", "libglib2.0-0", "libgomp1", "build-essential")
    .pip_install_from_requirements(str(SOURCE / "requirements.txt"))
    .add_local_dir(
        str(SOURCE),
        "/opt/PowerSim",
        copy=True,
        ignore=[".git/", "assets/", "data/", "outputs/", "__pycache__/"],
    )
    .env({
        "PYTHONPATH": "/opt/PowerSim:/opt/xplore",
        "PYTHONNOUSERSITE": "1",
        "OMP_NUM_THREADS": "4",
        "HF_HOME": "/data/huggingface",
        "WP_CACHE_DIR": "/data/warp-cache",
        "MPLCONFIGDIR": "/tmp/matplotlib",
    })
    .add_local_dir(str(ROOT / "backend"), "/opt/xplore/backend", ignore=[".venv/", "__pycache__/"])
)


@app.function(
    image=runtime_image,
    volumes={"/data": volume},
    cpu=2,
    memory=8192,
    timeout=600,
    max_containers=1,
    scaledown_window=2,
    retries=0,
)
def prepare():
    """Pin dataset revision and download only the three required scene files."""
    import hashlib
    import json
    import time

    from huggingface_hub import HfApi, snapshot_download

    started = time.monotonic()
    api = HfApi()
    revision = api.dataset_info("Tung11/PowerSim").sha
    patterns = [
        f"powerfoam_ckpt/{SCENE}/config.yaml",
        f"powerfoam_ckpt/{SCENE}/model.pt",
        f"powerfoam_ckpt/{SCENE}/cameras_train.pt",
        "README.md",
    ]
    directory = Path("/data/assets")
    snapshot_download(
        "Tung11/PowerSim", repo_type="dataset", revision=revision,
        local_dir=str(directory), allow_patterns=patterns,
    )
    files = {}
    for pattern in patterns:
        path = directory / pattern
        if not path.is_file():
            raise RuntimeError(f"Required released asset missing: {pattern}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        files[pattern] = {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}
    record = {
        "upstream_commit": UPSTREAM_COMMIT,
        "dataset": "Tung11/PowerSim",
        "dataset_revision": revision,
        "scene": SCENE,
        "files": files,
        "prepare_seconds": time.monotonic() - started,
    }
    (directory / "provenance.json").write_text(json.dumps(record, indent=2))
    volume.commit()
    return record


@app.function(
    image=runtime_image,
    gpu="L40S",
    volumes={"/data": volume},
    cpu=4,
    memory=16384,
    timeout=600,
    max_containers=1,
    scaledown_window=2,
    retries=0,
)
def baseline():
    """Reproduce the released pillow drop without changing physics settings."""
    import json
    import os
    import subprocess
    import sys
    import time

    import torch

    volume.reload()
    if not Path("/data/assets/provenance.json").is_file():
        raise RuntimeError("Run the prepare stage before using GPU time")
    os.chdir("/opt/PowerSim")
    directory = Path("/data/baseline/pillow-drop")
    if directory.exists():
        raise RuntimeError("Baseline directory already exists; inspect it before rerunning")
    directory.mkdir(parents=True)
    (directory / "environment.txt").write_text(
        subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    )
    command = [
        sys.executable, "-m", "powersim.foam_evolve.simulate",
        "--checkpoint-config", f"/data/assets/powerfoam_ckpt/{SCENE}/config.yaml",
        "--sim-config", "config/pillow_drop.json",
        "--split", "train", "--camera-index", "87",
        "--background", "1", "1", "1",
        "--output-dir", str(directory), "--compile-video", "--save-positions",
    ]
    started = time.monotonic()
    try:
        with (directory / "simulation.log").open("w") as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=550)
        elapsed = time.monotonic() - started
        if process.returncode:
            tail = (directory / "simulation.log").read_text()[-12000:]
            raise RuntimeError(f"PowerSim exited {process.returncode}:\n{tail}")
        position_files = sorted((directory / "positions").glob("positions_*.pt"))
        if len(position_files) != 150:
            raise RuntimeError(f"Expected 150 position frames, got {len(position_files)}")
        for file in position_files:
            state = torch.load(file, map_location="cpu", weights_only=True)
            if not torch.isfinite(state).all():
                raise RuntimeError(f"Nonfinite positions: {file.name}")
        video = directory / "output.mp4"
        if not video.is_file() or video.stat().st_size == 0:
            raise RuntimeError("Simulation did not produce a video")
        record = {
            "engine": "powersim",
            "upstream_commit": UPSTREAM_COMMIT,
            "scene": SCENE,
            "protocol": "released_pillow_drop",
            "frames": len(position_files),
            "positions_finite": True,
            "runtime_seconds": elapsed,
            "torch_version": str(torch.__version__),
            "cuda_version": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(),
            "video_bytes": video.stat().st_size,
            "video_path": str(video),
            "command": command,
            "metric_status": "not_yet_defined",
            "evidence_status": "simulation_only",
        }
        (directory / "manifest.json").write_text(json.dumps(record, indent=2))
        return record
    finally:
        volume.commit()


@app.function(image=inspection_image, volumes={"/data": volume}, timeout=30, retries=0)
def inspect_baseline():
    """Read the latest persisted snapshot without starting another GPU."""
    volume.reload()
    directory = Path("/data/baseline/pillow-drop")
    log = directory / "simulation.log"
    import json

    manifest = directory / "manifest.json"
    return {
        "snapshot_frame_count": len(list(directory.glob("frame_*.png"))),
        "log_tail": log.read_text()[-3000:] if log.exists() else "No persisted log yet",
        "completed_manifest_exists": (directory / "manifest.json").exists(),
        "manifest": json.loads(manifest.read_text()) if manifest.exists() else None,
    }


@app.local_entrypoint()
def main(stage: str = "prepare"):
    import json

    if stage == "prepare":
        result = prepare.remote()
    elif stage == "baseline":
        result = baseline.remote()
    elif stage == "inspect":
        result = inspect_baseline.remote()
    elif stage == "fetch":
        inspection = inspect_baseline.remote()
        result = inspection["manifest"]
        if result is None:
            raise RuntimeError("There is no completed baseline to fetch")
    else:
        raise ValueError("stage must be prepare, baseline, inspect, or fetch")
    result_name = "baseline" if stage == "fetch" else stage
    destination = ROOT / "docs" / f"{result_name}-result.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    if stage in ("baseline", "fetch"):
        preview = ROOT / "outputs" / "baseline"
        preview.mkdir(parents=True, exist_ok=True)
        for name in ("output.mp4", "frame_0000.png", "frame_0149.png", "environment.txt"):
            with (preview / name).open("wb") as stream:
                for chunk in volume.read_file(f"baseline/pillow-drop/{name}"):
                    stream.write(chunk)
        with (preview / "asset-README.md").open("wb") as stream:
            for chunk in volume.read_file("assets/README.md"):
                stream.write(chunk)
        print(f"Downloaded baseline video and stills to {preview}")
    print(json.dumps(result, indent=2))

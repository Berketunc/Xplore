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
DATASET_REVISION = "78e400018cb9fb20a0e5a62a9138805379055efb"
app = modal.App("xplore-simulation")
volume = modal.Volume.from_name("xplore-experiments", create_if_missing=True)
inspection_image = modal.Image.debian_slim(python_version="3.11")
record_mapping = modal.Dict.from_name("xplore-records-v1", create_if_missing=True)
claims = modal.Dict.from_name("xplore-compute-claims-v1", create_if_missing=True)
api_image = (
    inspection_image.pip_install("fastapi==0.121.0", "pydantic==2.14.3", "starlette==0.49.3")
    .env({"PYTHONPATH": "/opt/xplore"})
    .add_local_dir(str(ROOT / "backend"), "/opt/xplore/backend", ignore=[".venv/", "__pycache__/"])
    .add_local_dir(str(ROOT / "shared"), "/opt/xplore/shared")
)

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
    revision = DATASET_REVISION
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


@app.function(image=runtime_image, volumes={"/data": volume}, cpu=2, memory=8192, timeout=180)
def inspect_geometry():
    import json
    import numpy as np
    import torch
    from scipy.spatial import cKDTree
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    volume.reload()
    model = torch.load(f"/data/assets/powerfoam_ckpt/{SCENE}/model.pt", map_location="cpu", weights_only=True)
    points = model["points"].float().numpy()
    center = (points.min(0) + points.max(0)) / 2
    scale = 1 / np.ptp(points, axis=0).max()
    normalized = (points - center) * scale + 1
    # The released example holds its lower pillows around z=1.2 until t=.5.
    ids = np.flatnonzero((normalized[:, 2] > 1.08) & (normalized[:, 2] < 1.33))
    tree = cKDTree(normalized[ids])
    pairs = tree.query_pairs(.012, output_type="ndarray")
    graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(ids), len(ids)))
    count, labels = connected_components(graph, directed=False)
    groups = []
    directory = Path("/data/controlled")
    directory.mkdir(exist_ok=True)
    for label in np.argsort(np.bincount(labels))[::-1][:8]:
        selected = ids[labels == label]
        if len(selected) < 500:
            continue
        xyz = normalized[selected]
        group_id = f"component-{len(groups)}"
        mask = torch.zeros(len(points), dtype=torch.bool)
        mask[selected] = True
        torch.save(mask, directory / f"{group_id}.pt")
        groups.append({"id": group_id, "count": len(selected), "min": xyz.min(0).tolist(), "max": xyz.max(0).tolist(), "mean": xyz.mean(0).tolist()})
    result = {"particle_count": len(points), "components": groups, "z_quantiles": np.quantile(normalized[:, 2], [0,.25,.5,.75,.9,.95,1]).tolist()}
    (directory / "geometry.json").write_text(json.dumps(result, indent=2))
    volume.commit()
    return result


@app.function(image=runtime_image, gpu="L40S", volumes={"/data": volume}, cpu=4,
              memory=16384, timeout=600, max_containers=1, scaledown_window=2, retries=0)
def controlled(candidate="balanced", load=1., dt=.0001, frames=100, force=.005):
    import json
    import subprocess
    import threading
    from backend.controlled import run_candidate

    volume.reload()
    stop = threading.Event()
    samples = []

    def sample_memory():
        while not stop.is_set():
            try:
                text = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True, timeout=3)
                samples.append(int(text.strip().splitlines()[0]))
            except (subprocess.SubprocessError, ValueError):
                pass
            stop.wait(1.)

    monitor = threading.Thread(target=sample_memory, daemon=True)
    monitor.start()
    try:
        result = run_candidate(candidate, load, substep_dt=dt, frames=frames, force=force)
        stop.set()
        monitor.join(timeout=4)
        if result["execution_mode"] == "live":
            result["sampled_peak_gpu_memory_mib"] = max(samples) if samples else None
            result["memory_sampling_interval_seconds"] = 1.
            (Path(result["output_directory"]) / "manifest.json").write_text(json.dumps(result, indent=2))
        return result
    finally:
        stop.set()
        monitor.join(timeout=4)
        volume.commit()


@app.function(image=api_image, volumes={"/data": volume}, cpu=1, memory=512, timeout=120, retries=0)
def register_benchmark(results):
    import json
    from backend.records import create_record
    from backend.catalog import get_catalog
    from backend.jobs import execute_experiment
    from backend.store import RecordStore

    volume.reload()
    runs = results["candidates"]
    baseline = next(run for run in runs if run["candidate_id"] == "balanced")
    zero = results["zero_load"]
    refined = results["half_timestep"]
    reference_config = {key: value for key, value in baseline["config"].items() if key != "E"}
    if any({key: value for key, value in run["config"].items() if key != "E"} != reference_config for run in runs):
        raise ValueError("Candidate settings differ beyond stiffness")
    if zero["deformation_pct"] > .01:
        raise ValueError("Zero-load control is not sufficiently unchanged")
    difference = abs(refined["deformation_pct"] - baseline["deformation_pct"])
    relative = difference / max(baseline["deformation_pct"], .01)
    if any(run["support_drift_mpm"] / run["reference_length"] > .001 for run in runs):
        raise ValueError("Support drift exceeds 0.1% of reference separation")
    if any(run.get("sampled_courant_estimate", 0) > .4 for run in runs):
        raise ValueError("Observed speed and initial elastic wave-speed estimate exceed the configured Courant bound")
    registry = {
        "runs": {run["candidate_id"]: run["cache_key"] for run in runs},
        "load_multiplier": 1., "reference_force_per_particle": abs(baseline["config"]["boundary_conditions"][-1]["force"][2]),
        "substep_dt": baseline["config"]["substep_dt"],
        "zero_load_peak_pct": zero["deformation_pct"],
        "timestep_peak_difference_pp": difference, "timestep_relative_difference": relative,
        "timestep_control": refined["cache_key"], "zero_load_control": zero["cache_key"],
        "available": True,
        "validated": relative <= .05,
        "numerical_quality": {
            "status": "passed" if relative <= .05 else "timestep_sensitive",
            "timestep_goal_relative_change": .05,
            "timestep_relative_change": relative,
            "timestep_absolute_change_pp": difference,
            "baseline_dt": baseline["config"]["substep_dt"], "refined_dt": refined["config"]["substep_dt"],
            "baseline_peak_pct": baseline["deformation_pct"], "refined_peak_pct": refined["deformation_pct"],
            "note": f"Exploratory simulation: halving the timestep changed Balanced's peak compression by {relative:.1%} ({difference:.2f} percentage points). The 5% convergence goal {'passed' if relative <= .05 else 'was not met'}; {'physical validation remains pending' if relative <= .05 else 'the shortlist is provisional and near-threshold decisions may change'}. Physical agreement is not established.",
        },
    }
    (Path("/data/controlled") / "registry.json").write_text(json.dumps(registry, indent=2))
    volume.commit()
    store = RecordStore(record_mapping, volume=volume)
    test = get_catalog(available=True, numerical_quality=registry["numerical_quality"])["tests"][0]
    request = {"schema_version": "1.0", "test_id": test["test_id"],
        "candidate_ids": ["flexible", "balanced", "firm"], "load_multiplier": 1.,
        "target_max_deformation_pct": test["target"]["default"], "prototype_costs_gbp": {}}
    record = create_record(request, test)
    store.put(record["experiment_id"], record)
    result = execute_experiment(record["experiment_id"], store=store, registry=registry)
    out = Path("/data/examples")
    out.mkdir(exist_ok=True)
    (out / "example.json").write_text(json.dumps(result, indent=2))
    volume.commit()
    return {"registry": registry, "example_experiment_id": record["experiment_id"], "runs": runs}


@app.function(image=api_image, volumes={"/data": volume}, cpu=1, memory=1024, timeout=600,
              max_containers=1, scaledown_window=2, retries=0)
def process_experiment(identifier):
    import json
    from backend.jobs import execute_experiment
    from backend.store import RecordStore

    volume.reload()
    registry = json.loads(Path("/data/controlled/registry.json").read_text())
    store = RecordStore(record_mapping, volume=volume)

    def live(candidate_id, load):
        # At most one cache recovery per registered candidate. Public requests
        # cannot create arbitrary scenes, settings, loads, or repeated GPU work.
        claim = f"compression-v1:{candidate_id}:{registry['runs'][candidate_id]}"
        if not claims.put(claim, True, skip_if_exists=True):
            raise RuntimeError("A recovery for this simulation has already been attempted")
        result = controlled.remote(candidate_id, load, registry["substep_dt"], 100, registry["reference_force_per_particle"])
        volume.reload()
        return result

    return execute_experiment(identifier, store=store, registry=registry, run_live=live)


@app.function(image=api_image, volumes={"/data": volume}, cpu=1, memory=512, timeout=240,
              max_containers=1, scaledown_window=15)
@modal.concurrent(max_inputs=16)
@modal.asgi_app()
def api():
    import hashlib
    import json
    from backend.api import create_app
    from backend.catalog import get_catalog
    from backend.jobs import resolve_artifact, try_cached
    from backend.records import finish_record
    from backend.store import RecordStore

    volume.reload()
    registry_file = Path("/data/controlled/registry.json")
    registry = json.loads(registry_file.read_text()) if registry_file.exists() else {"runs": {}, "validated": False}
    store = RecordStore(record_mapping, volume=volume)

    def submit(identifier):
        return process_experiment.spawn(identifier).object_id

    def refresh(record):
        if record["status"] in ("completed", "partial", "failed"):
            return record
        call = store.get("call:" + record["experiment_id"])
        if not call:
            return record
        try:
            modal.FunctionCall.from_id(call["function_call_id"]).get(timeout=0)
        except TimeoutError:
            return record
        except Exception:
            for run in record["runs"]:
                if run["status"] in ("queued", "running"):
                    run.update({"status": "failed", "error": {"code": "worker_stopped", "message": "The worker stopped before completing this candidate."}})
            finish_record(record)
            store.put(record["experiment_id"], record)
            return record
        return store.get(record["experiment_id"])

    def artifact_path(record, filename):
        # Copy approved immutable files to local disk so a browser streaming a
        # video never keeps a Volume file open during a later Volume reload.
        with store.lock:
            volume.reload()
            if record is not None and filename == "experiment.json":
                payload = json.dumps(record, indent=2).encode()
            else:
                source = resolve_artifact(record, filename, registry=registry)
                if source is None or not source.is_file():
                    return None
                payload = source.read_bytes()
            destination = Path("/tmp/xplore-artifacts") / hashlib.sha256(payload).hexdigest() / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            return destination

    result = create_app(store=store, submit=submit,
        catalog=lambda: get_catalog(available=registry.get("available", False), numerical_quality=registry.get("numerical_quality")),
        artifact_path=artifact_path, refresh=refresh,
        resolve_cached=lambda record: try_cached(record, registry=registry))
    from backend.live_api import install_interactive_routes
    install_interactive_routes(result, claims=claims, volume=volume, stream_function=stream_physics)
    return result


@app.function(image=runtime_image, gpu=["L4", "L40S", "A10", "T4"], volumes={"/data": volume}, cpu=4, memory=8192,
              timeout=180, startup_timeout=90, max_containers=1, scaledown_window=30)
def stream_physics(commands, candidate):
    import queue
    import threading
    import time
    from backend.interactive import InteractivePhysics

    volume.reload()
    model = InteractivePhysics(candidate)
    model.substeps = 33
    model.step()
    volume.commit()  # Persist compiled Warp kernels for later cold starts.
    local_commands = queue.Queue()
    stop = threading.Event()

    def receive_commands():
        while not stop.is_set():
            try:
                for item in commands.get_many(100, timeout=.2):
                    local_commands.put(item)
            except queue.Empty:
                pass
            except Exception:
                stop.set()

    receiver = threading.Thread(target=receive_commands, daemon=True)
    receiver.start()
    started = time.monotonic()
    yield {"type": "ready", "mesh": model.mesh, "candidate_id": candidate, "max_live_seconds": 90}
    try:
        while time.monotonic()-started < 90 and not stop.is_set():
            frame_started = time.monotonic()
            while not local_commands.empty():
                item = local_commands.get_nowait()
                if item["type"] == "stop":
                    return
                if item["type"] == "grab":
                    model.grab_point(item["point"], item["target"])
                elif item["type"] == "move":
                    model.move(item["target"])
                elif item["type"] == "release":
                    model.release()
                elif item["type"] == "reset":
                    model = InteractivePhysics(candidate)
                    model.substeps = 33
            positions = model.step()
            yield {"type": "frame", "positions": positions, "sequence": model.frame,
                "simulation_time": model.frame*model.dt*model.substeps,
                "remaining_seconds": max(0,90-(time.monotonic()-started))}
            stop.wait(max(0,1/30-(time.monotonic()-frame_started)))
        yield {"type": "ended", "reason": "session_limit"}
    finally:
        stop.set()
        receiver.join(timeout=1)


@app.function(image=runtime_image, gpu="L40S", volumes={"/data": volume}, cpu=4, memory=8192,
              timeout=180, max_containers=1, scaledown_window=2, retries=0)
def interactive_benchmark():
    from backend.interactive import benchmark

    volume.reload()
    try:
        return benchmark()
    finally:
        volume.commit()


@app.local_entrypoint()
def main(stage: str = "prepare", candidate: str = "balanced", load: float = 1.,
         dt: float = .0001, frames: int = 100, force: float = .005):
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
    elif stage == "geometry":
        result = inspect_geometry.remote()
    elif stage == "controlled":
        result = controlled.remote(candidate, load, dt, frames, force)
    elif stage == "benchmark":
        runs = []
        for cid in ("balanced", "firm", "flexible"):
            run = controlled.remote(cid, 1., dt, 100, force)
            runs.append(run)
            print(f"{cid}: {run['deformation_pct']:.4f}% peak; {run['runtime_seconds']:.2f}s; {run['cache_key']}", flush=True)
        zero = controlled.remote("balanced", 1., dt, 100, 0.)
        print(f"Zero-load peak: {zero['deformation_pct']:.6f}%", flush=True)
        refined = controlled.remote("balanced", 1., dt/2, 100, force)
        print(f"Half-timestep peak: {refined['deformation_pct']:.6f}%", flush=True)
        result = register_benchmark.remote({"candidates": runs, "zero_load": zero, "half_timestep": refined})
    elif stage == "probe-load":
        original = controlled.remote("balanced", 1., dt, 100, force)
        print(f"Load probe peak: {original['deformation_pct']:.6f}%", flush=True)
        refined = controlled.remote("balanced", 1., dt/2, 100, force)
        result = {"original": original, "refined": refined,
            "relative_difference": abs(original["deformation_pct"]-refined["deformation_pct"])/max(original["deformation_pct"], .01)}
    elif stage == "interactive-benchmark":
        result = interactive_benchmark.remote()
    else:
        raise ValueError(f"Unknown stage: {stage}")
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
    if stage == "controlled":
        preview = ROOT / "outputs" / candidate
        preview.mkdir(parents=True, exist_ok=True)
        remote_path = result["output_directory"].removeprefix("/data/")
        for name in ("output.mp4", "reference.png", f"frame_{frames-1:04d}.png", "measurements.json"):
            with (preview / name).open("wb") as stream:
                for chunk in volume.read_file(f"{remote_path}/{name}"):
                    stream.write(chunk)
    if stage == "benchmark":
        for run in result["runs"]:
            preview = ROOT / "outputs" / run["candidate_id"]
            preview.mkdir(parents=True, exist_ok=True)
            for name in ("output.mp4", "still.png", "final.png", "measurements.json"):
                with (preview / name).open("wb") as stream:
                    for chunk in volume.read_file(f"runs/{run['cache_key']}/{name}"):
                        stream.write(chunk)
    print(json.dumps({key: value for key, value in result.items() if key not in ("time_series", "config")}, indent=2))

"""Approved single-pillow compression setup and PowerSim subprocess runner."""

from pathlib import Path

UPSTREAM_COMMIT = "24266e5264a213bceb426796ce91e12a555e2f69"
RUNNER_VERSION = "compression-v1"
CANDIDATES = {"flexible": .5, "balanced": 1., "firm": 2.}
DATASET_REVISION = "78e400018cb9fb20a0e5a62a9138805379055efb"


def prepare_scene(directory=Path("/data/controlled")):
    import hashlib
    import json
    import numpy as np
    import torch

    source = Path("/data/assets/powerfoam_ckpt/pillow2sofa_gs_fewer_points")
    points = torch.load(source / "model.pt", map_location="cpu", weights_only=True)["points"].float()
    mask = torch.load(directory / "component-0.pt", map_location="cpu", weights_only=True)
    selected = points[mask]
    if len(selected) != 25104:
        raise ValueError("Selected scene identity changed")
    torch.save(~mask, directory / "hide.pt")
    length = (selected.max(0).values - selected.min(0).values).max()
    normalized = (selected - (selected.min(0).values + selected.max(0).values) / 2) / length + 1
    z = normalized[:, 2].numpy()
    bottom, top = np.quantile(z, [.15, .85]).tolist()
    upper = np.flatnonzero(z >= top).tolist()
    lower = np.flatnonzero(z <= bottom).tolist()
    groups = {
        "scene_setup_version": 2,
        "upper": upper, "lower": lower, "axis": [0, 0, 1],
        "particle_ids": mask.nonzero(as_tuple=True)[0].tolist(),
        "reference_length": float(normalized[upper, 2].mean() - normalized[lower, 2].mean()),
        "top_threshold": top, "bottom_threshold": bottom,
        "selection_sha256": hashlib.sha256(mask.numpy().tobytes()).hexdigest(),
        "definition": "Upper and lower 15% by initial MPM z coordinate, fixed scene particle IDs",
    }
    # Preserve the released camera/ray model. Crop its rendered output consistently.
    bundle = torch.load(source / "cameras_train.pt", map_location="cpu", weights_only=True)
    eye = bundle["eyes"][87].float()
    right, up = bundle["rights"][87].float(), bundle["ups"][87].float()
    forward = torch.nn.functional.normalize(torch.linalg.cross(up, right), dim=0)
    d = selected - eye
    depth = d @ forward
    width, height = bundle["img_wh"]
    col = ((d @ right) / (depth * right.square().sum()) + 1) * (width - 1) / 2
    row = (1 - (d @ up) / (depth * up.square().sum())) * (height - 1) / 2
    side = int(max(float(col.max()-col.min()), float(row.max()-row.min())) * 1.8)
    side = min(width, height, side + side % 2)
    crop_x = max(0, min(width-side, int(float((col.max()+col.min())/2)-side/2)))
    crop_y = max(0, min(height-side, int(float((row.max()+row.min())/2)-side/2)))
    groups["render_crop"] = {"x": crop_x, "y": crop_y, "size": side}
    (directory / "groups.json").write_text(json.dumps(groups, indent=2))
    checkpoint = directory / "checkpoint"
    checkpoint.mkdir(exist_ok=True)
    (checkpoint / "config.yaml").write_bytes((source / "config.yaml").read_bytes())
    model = checkpoint / "model.pt"
    if not model.exists():
        model.symlink_to(source / "model.pt")
    torch.save(bundle, checkpoint / "cameras_train.pt")
    return groups


def make_config(candidate_id, load_multiplier=1., *, substep_dt=.0001, frames=100, force=.005):
    import json

    if candidate_id not in CANDIDATES:
        raise ValueError("Unsupported candidate")
    groups = json.loads(Path("/data/controlled/groups.json").read_text())
    z0, z1 = groups["bottom_threshold"], groups["top_threshold"]
    # Fixed particle masks are selected at t=0 by the upstream solver.
    lower_point = [1, 1, (z0 + .4) / 2]
    lower_size = [1, 1, (z0 - .4) / 2]
    load_duration = .1
    return {
        "material": "jelly", "n_grid": 100, "grid_lim": 2.,
        "E": 10000. * CANDIDATES[candidate_id], "nu": .3, "density": 2000,
        "g": [0, 0, 0], "grid_v_damping_scale": .9999 ** (substep_dt / .0001),
        "substep_dt": substep_dt, "frame_dt": .02, "frame_num": frames,
        "scale": 1., "rotation_degree": [], "rotation_axis": [],
        "boundary_conditions": [
            {"type": "bounding_box"},
            {"type": "cuboid", "point": lower_point, "size": lower_size,
             "velocity": [0, 0, 0], "start_time": 0., "end_time": 1000.},
            {"type": "enforce_particle_translation", "point": lower_point, "size": lower_size,
             "velocity": [0, 0, 0], "start_time": 0., "end_time": 1000.},
            {"type": "particle_impulse", "force": [0, 0, -force * load_multiplier],
             "point": [1, 1, (z1 + 1.6) / 2], "size": [1, 1, (1.6 - z1) / 2],
             "num_dt": round(load_duration / substep_dt), "start_time": 0.},
        ],
        "default_camera_index": 87,
    }


def run_candidate(candidate_id, load_multiplier=1., *, substep_dt=.0001, frames=100, force=.005):
    import hashlib
    import json
    import os
    import shutil
    import subprocess
    import sys
    import time
    import numpy as np
    import torch

    from backend.metrics import deformation_series
    from backend import state_export
    from backend.state_export import apply_export_adapter

    directory = Path("/data/controlled")
    if not (directory / "groups.json").exists() or json.loads((directory / "groups.json").read_text()).get("scene_setup_version") != 2:
        prepare_scene(directory)
    groups = json.loads((directory / "groups.json").read_text())
    config = make_config(candidate_id, load_multiplier, substep_dt=substep_dt, frames=frames, force=force)
    identity = {
        "config": config, "runner": RUNNER_VERSION, "upstream": UPSTREAM_COMMIT,
        "dataset": DATASET_REVISION, "groups": groups,
        "camera_sha256": hashlib.sha256((directory / "checkpoint/cameras_train.pt").read_bytes()).hexdigest(),
        "seed": 0, "export_adapter": "xplore-state-export-v1",
        "adapter_source_sha256": hashlib.sha256(Path(state_export.__file__).read_bytes()).hexdigest(),
        "runner_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    cache_key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    output = Path("/data/runs") / cache_key
    manifest = output / "manifest.json"
    if manifest.exists():
        result = json.loads(manifest.read_text())
        result["execution_mode"] = "cached"
        return result
    if output.exists():
        raise RuntimeError(f"Prior incomplete run retained for inspection: {cache_key}")
    output.mkdir(parents=True)
    (output / "config.json").write_text(json.dumps(config, indent=2))
    (output / "groups.json").write_text(json.dumps(groups, indent=2))
    # A fresh copy of just the simulation module is patched; all imports use pinned source.
    source = Path("/opt/PowerSim/powersim/foam_evolve/simulate.py")
    adapter_path = output / "simulate_xplore.py"
    shutil.copyfile(source, adapter_path)
    patch = apply_export_adapter(adapter_path)
    command = [sys.executable, str(adapter_path),
        "--checkpoint-config", str(directory / "checkpoint/config.yaml"),
        "--sim-config", str(output / "config.json"),
        "--selection", str(directory / "component-0.pt"), "--hide", str(directory / "hide.pt"),
        "--split", "train", "--camera-index", "87", "--background", "1", "1", "1",
        "--output-dir", str(output), "--save-positions"]
    os.chdir("/opt/PowerSim")
    started = time.monotonic()
    with (output / "simulation.log").open("w") as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=490)
    if process.returncode:
        raise RuntimeError((output / "simulation.log").read_text()[-6000:])
    (output / "execution.json").write_text(json.dumps({"simulation_seconds": time.monotonic() - started}))
    (output / "run_metadata.json").write_text(json.dumps({"candidate_id": candidate_id, "cache_key": cache_key, "export_patch": patch}))
    return finalize_run(output)


def finalize_run(output):
    import hashlib
    import json
    import shutil
    import subprocess
    import time
    import numpy as np
    import torch
    from backend.metrics import deformation_series

    output = Path(output)
    started = time.monotonic()
    config = json.loads((output / "config.json").read_text())
    groups = json.loads((output / "groups.json").read_text())
    frames = config["frame_num"]
    cache_key = output.name
    candidate_id = next(cid for cid, factor in CANDIDATES.items() if config["E"] == 10000. * factor)
    patch = {
        "adapter": "xplore-state-export-v1",
        "original_sha256": hashlib.sha256(Path("/opt/PowerSim/powersim/foam_evolve/simulate.py").read_bytes()).hexdigest(),
        "patched_sha256": hashlib.sha256((output / "simulate_xplore.py").read_bytes()).hexdigest(),
    }
    state_path = output / "xplore_state"
    reference = torch.load(state_path / "reference.pt", map_location="cpu", weights_only=True)
    if reference["particle_ids"].tolist() != groups["particle_ids"]:
        raise ValueError("Exported particle IDs do not match the fixed measurement groups")
    positions, times, speeds = [], [], []
    files = sorted(state_path.glob("frame_*.pt"))
    if len(files) != frames:
        raise ValueError("Incomplete state export")
    for file in files:
        sample = torch.load(file, map_location="cpu", weights_only=True)
        positions.append(sample["positions_mpm"].numpy())
        times.append(sample["time"])
        if "max_speed_mpm" in sample:
            speeds.append(sample["max_speed_mpm"])
    measurement = deformation_series(reference["positions_mpm"].numpy(), positions, times,
        upper=groups["upper"], lower=groups["lower"], axis=groups["axis"], metric="compression")
    metadata = json.loads((state_path / "metadata.json").read_text())
    support_drift = max(float(np.linalg.norm(p[groups["lower"]].mean(0) - reference["positions_mpm"].numpy()[groups["lower"]].mean(0))) for p in positions)
    video_frames = output / "video_frames"
    video_frames.mkdir(exist_ok=True)
    shutil.copyfile(output / "reference.png", video_frames / "frame_0000.png")
    for i in range(frames):
        shutil.copyfile(output / f"frame_{i:04d}.png", video_frames / f"frame_{i+1:04d}.png")
    crop = groups["render_crop"]
    video_filter = f"crop={crop['size']}:{crop['size']}:{crop['x']}:{crop['y']},scale=448:448"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "50", "-i", str(video_frames / "frame_%04d.png"),
        "-vf", video_filter, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output / "output.mp4")], check=True, timeout=20)
    for source_name, target_name in (("reference.png", "still.png"), (f"frame_{frames-1:04d}.png", "final.png")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(output/source_name), "-vf", video_filter, "-frames:v", "1", str(output/target_name)], check=True, timeout=10)
    from PIL import Image
    if int((np.asarray(Image.open(output / "still.png")).min(axis=2) < 240).sum()) < 100:
        raise ValueError("Rendered reference is blank")
    execution = output / "execution.json"
    runtime = json.loads(execution.read_text())["simulation_seconds"] + time.monotonic() - started if execution.exists() else None
    series = {
        "t": [s["time"] for s in measurement["time_series"]],
        "deformation_pct": [s["deformation_pct"] for s in measurement["time_series"]],
        "t_unit": "simulation_s", "sample_interval": metadata["frame_dt"],
    }
    (output / "measurements.json").write_text(json.dumps({**measurement, "time_series": series}, indent=2))
    (output / "measurements.csv").write_text("simulation_s,deformation_pct\n" + "".join(f"{t},{d}\n" for t,d in zip(series["t"], series["deformation_pct"])))
    result = {
        "candidate_id": candidate_id, "status": "completed", "engine": "powersim",
        "execution_mode": "live", "cache_key": cache_key, "metric_id": "compression_pct",
        "deformation_pct": measurement["deformation_pct"], "time_series": series,
        "video_url": None, "runtime_seconds": runtime, "error": None,
        "output_directory": str(output), "reference_length": measurement["reference_length"],
        "support_drift_mpm": support_drift, "position_dtype": "float32",
        "config": config, "versions": {"runner": RUNNER_VERSION, "powersim_commit": UPSTREAM_COMMIT},
        "export_patch": patch,
    }
    if speeds:
        import math
        mu = config["E"] / (2 * (1 + config["nu"]))
        lam = config["E"] * config["nu"] / ((1+config["nu"])*(1-2*config["nu"]))
        wave = math.sqrt((lam + 2*mu) / config["density"])
        result["sampled_max_particle_speed_mpm"] = max(speeds)
        result["initial_elastic_wave_speed_estimate"] = wave
        result["sampled_courant_estimate"] = (max(speeds)+wave) * config["substep_dt"] / (config["grid_lim"]/config["n_grid"])
    (output / "manifest.json").write_text(json.dumps(result, indent=2))
    return result

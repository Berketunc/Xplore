"""Durable experiment processing with genuine versioned simulation artifacts."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from backend.records import finish_record


ALLOWED_ARTIFACTS = {"mp4": "output.mp4", "png": "still.png", "json": "measurements.json", "csv": "measurements.csv",
    "groups.json": "groups.json", "config.json": "config.json", "state-metadata.json": "xplore_state/metadata.json"}


def attach_artifacts(run, identifier):
    run = deepcopy(run)
    for extension in ALLOWED_ARTIFACTS:
        url = f"/v1/artifacts/{identifier}/{run['candidate_id']}.{extension}"
        run.setdefault("artifact_urls", {})[extension] = url
        if "." not in extension:
            run[f"artifact_{extension}"] = url
    run["video_url"] = run["artifact_mp4"]
    run["still_url"] = run["artifact_png"]
    run["reference_time"] = 0.
    run["video_sample_interval"] = .02
    return run


def finalize_record(record, registry):
    record["config_hash"] = hashlib.sha256(json.dumps([run["cache_key"] for run in record["runs"]]).encode()).hexdigest()
    finish_record(record)
    quality = registry.get("numerical_quality")
    if quality:
        record["numerical_quality"] = deepcopy(quality)
        if quality["status"] == "timestep_sensitive":
            record["selection"]["provisional"] = True
            record["selection"]["notes"].append(quality["note"])
    return record


def try_cached(record, *, registry, runs_root=Path("/data/runs")):
    completed = deepcopy(record)
    for index, run in enumerate(completed["runs"]):
        key = registry["runs"].get(run["candidate_id"])
        if key is None:
            return None
        manifest = runs_root / key / "manifest.json"
        if not manifest.is_file():
            return None
        cached = json.loads(manifest.read_text())
        if cached["status"] != "completed" or cached["cache_key"] != key:
            return None
        cached["execution_mode"] = "cached"
        completed["runs"][index] = attach_artifacts(cached, record["experiment_id"])
    return finalize_record(completed, registry)


def execute_experiment(identifier, *, store, registry, run_live=None, runs_root=Path("/data/runs")):
    record = store.get(identifier)
    if record["status"] in ("completed", "partial", "failed"):
        return record
    record["status"] = "running"
    store.put(identifier, record)
    for i, pending in enumerate(record["runs"]):
        cid = pending["candidate_id"]
        pending["status"] = "running"
        store.put(identifier, record)
        try:
            key = registry["runs"][cid]
            manifest = runs_root / key / "manifest.json"
            if manifest.exists():
                run = json.loads(manifest.read_text())
                run["execution_mode"] = "cached"
            elif run_live is not None:
                run = run_live(cid, record["request"]["load_multiplier"])
            else:
                raise RuntimeError("Registered result is missing")
            if run["status"] != "completed" or run["cache_key"] != key:
                raise RuntimeError("Worker result does not match registered physics identity")
            record["runs"][i] = attach_artifacts(run, identifier)
        except Exception:
            pending.update({"status": "failed", "error": {"code": "worker_error", "message": "The simulation result is unavailable; see the saved worker log."}})
        record["completed_runs"] = sum(run["status"] == "completed" for run in record["runs"])
        store.put(identifier, record)
    finalize_record(record, registry)
    store.put(identifier, record)
    return record


def resolve_artifact(record, filename, *, registry, root=Path("/data")):
    if record is None:
        if filename not in ("reference.png", "example.json"):
            return None
        if filename == "example.json":
            return root / "examples/example.json"
        key = registry["runs"].get("balanced")
        return root / "runs" / key / "still.png" if key else None
    if filename == "experiment.json":
        return root / "experiments" / (record["experiment_id"] + ".json")
    for run in record["runs"]:
        if run["status"] != "completed":
            continue
        for suffix, approved_name in ALLOWED_ARTIFACTS.items():
            if filename == f"{run['candidate_id']}.{suffix}":
                key = run["cache_key"]
                if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
                    return None
                path = root / "runs" / key / approved_name
                return path if path.resolve().is_relative_to((root / "runs").resolve()) else None
    return None

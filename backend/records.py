"""Experiment records independent of HTTP and the GPU implementation."""

from copy import deepcopy
from datetime import datetime, timezone
import uuid

from backend.ranking import select_candidates


def now():
    return datetime.now(timezone.utc).isoformat()


def create_record(request, test):
    return {
        "schema_version": "1.0", "experiment_id": "xplore-" + uuid.uuid4().hex,
        "fixture": False, "status": "queued", "completed_runs": 0,
        "total_runs": len(request["candidate_ids"]), "selection": None,
        "evidence_status": "simulation_only", "request": deepcopy(request),
        "unit_system": deepcopy(test["unit_system"]), "assumptions": list(test["assumptions"]),
        "created_at": now(), "completed_at": None,
        "versions": {"api": "1.0", "runner": "compression-v1", "powersim_commit": "24266e5264a213bceb426796ce91e12a555e2f69"},
        "checkpoint_id": "Tung11/PowerSim@78e400018cb9fb20a0e5a62a9138805379055efb/pillow2sofa_gs_fewer_points",
        "config_hash": None,
        "runs": [{
            "candidate_id": cid, "status": "queued", "engine": "powersim", "execution_mode": None,
            "cache_key": None, "metric_id": test["metric"]["metric_id"], "deformation_pct": None,
            "time_series": None, "video_url": None, "still_url": None,
            "runtime_seconds": None, "error": None,
        } for cid in request["candidate_ids"]],
    }


def finish_record(record):
    statuses = [run["status"] for run in record["runs"]]
    record["completed_runs"] = statuses.count("completed")
    record["status"] = "completed" if all(s == "completed" for s in statuses) else "failed" if all(s == "failed" for s in statuses) else "partial"
    record["completed_at"] = now()
    record["selection"] = select_candidates(record["runs"], record["request"]["candidate_ids"],
        record["request"]["target_max_deformation_pct"], record["request"].get("prototype_costs_gbp", {}))
    return record


def make_summary(record, test):
    definitions = {candidate["candidate_id"]: candidate for candidate in test["candidates"]}
    outcomes = {entry["candidate_id"]: entry["outcome"] for entry in (record.get("selection") or {}).get("candidates", [])}
    result = {
        "schema_version": "1.0", "experiment_id": record["experiment_id"],
        "fixture": record["fixture"], "status": record["status"], "evidence_status": record["evidence_status"],
        "test": {key: deepcopy(test[key]) for key in ("test_id", "title", "protocol", "metric")} | {"scene": test["scene"]["display_name"]},
        "load_multiplier": record["request"]["load_multiplier"], "unit_system": record["unit_system"],
        "candidates": [{key: run[key] for key in ("candidate_id", "status", "engine", "execution_mode", "deformation_pct")} | {
            "label": definitions[run["candidate_id"]]["label"], "outcome": outcomes.get(run["candidate_id"], "not_evaluated"),
            "prototype_cost_gbp": record["request"].get("prototype_costs_gbp", {}).get(run["candidate_id"]),
        } for run in record["runs"]],
        "selection": record["selection"], "assumptions": record["assumptions"],
        "limitations": ["Physical validation is pending.", "Reported values are normalized deformation in a dimensionless scene.", "Prototype costs are user-provided assumptions."],
    }
    if record.get("numerical_quality"):
        result["numerical_quality"] = record["numerical_quality"]
        if record["numerical_quality"]["status"] == "timestep_sensitive":
            result["limitations"].insert(0, record["numerical_quality"]["note"])
    return result

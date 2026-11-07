"""Exercise the deployed API and save genuine result clips for local inspection."""

import argparse
import json
import math
from pathlib import Path
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from shared.validate import check


def require_schema(value, name):
    errors = check(value, name)
    if errors:
        raise AssertionError(errors)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    arguments = parser.parse_args()
    base = arguments.base_url.rstrip("/")
    started = time.monotonic()
    with httpx.Client(base_url=base, timeout=90., follow_redirects=True) as client:
        health = client.get("/health")
        health.raise_for_status()
        require_schema(health.json(), "Health")
        catalog = client.get("/v1/catalog").json()
        require_schema(catalog, "Catalog")
        test = next(t for t in catalog["tests"] if t["availability"] == "available")
        request = {"schema_version": "1.0", "test_id": test["test_id"],
            "candidate_ids": ["flexible", "balanced", "firm"], "load_multiplier": 1.,
            "target_max_deformation_pct": test["target"]["default"], "prototype_costs_gbp": {"flexible": 2., "balanced": 3., "firm": 5.}}
        comparison_started = time.monotonic()
        submitted = client.post("/v1/experiments", json=request)
        assert submitted.status_code == 202, submitted.text
        record = submitted.json()
        require_schema(record, "Experiment")
        identifier = record["experiment_id"]
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            record = client.get(f"/v1/experiments/{identifier}").json()
            require_schema(record, "Experiment")
            if record["status"] in ("completed", "partial", "failed"):
                break
            time.sleep(2)
        assert record["status"] == "completed", record
        comparison_elapsed = time.monotonic() - comparison_started
        assert record["fixture"] is False and record["evidence_status"] == "simulation_only"
        assert all(r["execution_mode"] == "cached" for r in record["runs"])
        summary = client.get(f"/v1/experiments/{identifier}/summary").json()
        require_schema(summary, "Summary")
        assert summary["selection"] == record["selection"]
        out = ROOT / "outputs" / "deployed"
        out.mkdir(parents=True, exist_ok=True)
        for run in record["runs"]:
            assert math.isfinite(run["deformation_pct"])
            assert len(run["time_series"]["t"]) == 101
            partial = client.get(run["video_url"], headers={"Range": "bytes=0-127"})
            assert partial.status_code == 206, partial.text[:200]
            assert partial.headers["content-range"].startswith("bytes 0-127/")
            video = client.get(run["video_url"])
            video.raise_for_status()
            (out / f"{run['candidate_id']}.mp4").write_bytes(video.content)
            measurements = client.get(run["artifact_json"]).json()
            assert measurements["deformation_pct"] == run["deformation_pct"]
            csv = client.get(run["artifact_csv"])
            assert len(csv.text.strip().splitlines()) == 102
        bad = client.post("/v1/experiments", json=request | {"candidate_ids": ["unsupported"]})
        assert bad.status_code == 422
        require_schema(bad.json(), "ApiError")
        blocked = client.get(f"/v1/artifacts/{identifier}/simulation.log")
        assert blocked.status_code == 404
        changed = client.post("/v1/experiments", json=request | {"target_max_deformation_pct": 1., "prototype_costs_gbp": {}})
        assert changed.status_code == 202
        second_id = changed.json()["experiment_id"]
        for attempt in range(30):
            second = client.get(f"/v1/experiments/{second_id}").json()
            if second["status"] == "completed":
                break
            time.sleep(2)
        assert second["status"] == "completed"
        assert [r["cache_key"] for r in second["runs"]] == [r["cache_key"] for r in record["runs"]]
        assert second["selection"]["recommended_candidate_id"] is None
        cors = client.options("/v1/experiments", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
        assert cors.status_code == 200 and cors.headers.get("access-control-allow-origin") in ("*", "http://localhost:5173")
    with httpx.Client(base_url=base, timeout=30.) as fresh_client:
        assert fresh_client.get(f"/v1/experiments/{identifier}").json()["runs"] == record["runs"]
    result = {"api_base_url": base, "experiment_id": identifier,
        "verification_seconds": time.monotonic() - started, "cached_comparison_seconds": comparison_elapsed,
        "runs": [{key: r[key] for key in ("candidate_id", "deformation_pct", "runtime_seconds", "execution_mode", "video_url")} for r in record["runs"]],
        "selection": record["selection"],
        "checks": ["frozen schema", "submit/poll", "summary", "cached physics reuse", "range requests", "CSV/JSON artifacts", "invalid input", "artifact allowlist", "CORS", "saved record restore"]}
    (ROOT / "docs/deployment-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

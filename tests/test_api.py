from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient
from backend.api import create_app
from backend.catalog import get_catalog
from backend.jobs import execute_experiment, resolve_artifact, try_cached
from backend.store import RecordStore
from shared.validate import check


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mapping = {}
        self.store = RecordStore(self.mapping, self.root / "experiments")
        self.scheduled = []
        self.catalog = get_catalog(available=True)
        self.request = {"schema_version": "1.0", "test_id": "cushion-compression-v1",
            "candidate_ids": ["flexible", "balanced", "firm"], "load_multiplier": 1.,
            "target_max_deformation_pct": 20., "prototype_costs_gbp": {"flexible": 2., "balanced": 3., "firm": 5.}}
        self.registry = {"runs": {cid: str(i)*64 for i, cid in enumerate(self.request["candidate_ids"], 1)}}
        for cid, value in zip(self.request["candidate_ids"], [40., 18., 10.]):
            directory = self.root / "runs" / self.registry["runs"][cid]
            directory.mkdir(parents=True)
            manifest = {"candidate_id": cid, "status": "completed", "engine": "powersim", "execution_mode": "live",
                "cache_key": self.registry["runs"][cid], "metric_id": "compression_pct", "deformation_pct": value,
                "time_series": {"t": [0., 2.], "deformation_pct": [0., value], "t_unit": "simulation_s", "sample_interval": 2.},
                "video_url": None, "runtime_seconds": 1., "error": None}
            (directory / "manifest.json").write_text(json.dumps(manifest))
            (directory / "output.mp4").write_bytes(bytes(range(100)))
        self.client = self.make_client()

    def make_client(self):
        return TestClient(create_app(store=self.store, submit=lambda identifier: self.scheduled.append(identifier),
            catalog=lambda: deepcopy(self.catalog), artifact_path=lambda record, name: resolve_artifact(record, name, registry=self.registry, root=self.root)))

    def submit_and_finish(self, request=None):
        response = self.client.post("/v1/experiments", json=request or self.request)
        self.assertEqual(response.status_code, 202, response.text)
        identifier = response.json()["experiment_id"]
        execute_experiment(identifier, store=self.store, registry=self.registry, runs_root=self.root / "runs")
        return identifier

    def assert_contract(self, value, definition):
        self.assertEqual(check(value, definition), [])

    def test_catalog_queued_completed_and_summary_match_frozen_schema(self):
        self.assert_contract(self.client.get("/health").json(), "Health")
        self.assert_contract(self.client.get("/v1/catalog").json(), "Catalog")
        queued = self.client.post("/v1/experiments", json=self.request)
        self.assert_contract(queued.json(), "Experiment")
        self.assertIsNone(queued.json()["runs"][0]["deformation_pct"])
        identifier = self.submit_and_finish()
        completed = self.client.get(f"/v1/experiments/{identifier}").json()
        self.assert_contract(completed, "Experiment")
        self.assertEqual(completed["selection"]["recommended_candidate_id"], "balanced")
        self.assertTrue(all(run["execution_mode"] == "cached" for run in completed["runs"]))
        self.assert_contract(self.client.get(f"/v1/experiments/{identifier}/summary").json(), "Summary")

    def test_invalid_inputs_are_rejected_before_scheduling(self):
        cases = [{"candidate_ids": ["unknown"]}, {"candidate_ids": ["firm", "firm"]},
            {"load_multiplier": 2.}, {"prototype_costs_gbp": {"firm": -1}},
            {"prototype_costs_gbp": {"unknown": 1}}, {"target_max_deformation_pct": True}, {"extra": "field"}]
        for change in cases:
            response = self.client.post("/v1/experiments", json=self.request | change)
            self.assertEqual(response.status_code, 422, response.text)
            self.assert_contract(response.json(), "ApiError")
        self.assertEqual(self.scheduled, [])

    def test_nonfinite_values_are_rejected_with_valid_error_json(self):
        body = json.dumps(self.request).replace('"load_multiplier": 1.0', '"load_multiplier": NaN')
        response = self.client.post("/v1/experiments", content=body, headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.assert_contract(response.json(), "ApiError")

    def test_changed_costs_and_target_reuse_physics(self):
        first = self.submit_and_finish()
        modified = self.request | {"target_max_deformation_pct": 12., "prototype_costs_gbp": {}}
        second = self.submit_and_finish(modified)
        a, b = self.store.get(first), self.store.get(second)
        self.assertNotEqual(first, second)
        self.assertEqual([r["cache_key"] for r in a["runs"]], [r["cache_key"] for r in b["runs"]])
        self.assertEqual(b["selection"]["shortlist"], ["firm"])
        self.assertIsNone(b["selection"]["recommended_candidate_id"])

    def test_missing_artifact_gives_partial_provisional_result(self):
        (self.root / "runs" / self.registry["runs"]["flexible"] / "manifest.json").unlink()
        identifier = self.submit_and_finish()
        record = self.store.get(identifier)
        self.assertEqual(record["status"], "partial")
        self.assertTrue(record["selection"]["provisional"])
        self.assertIsNone(record["runs"][0]["deformation_pct"])
        self.assert_contract(record, "Experiment")

    def test_record_restores_without_process_local_mapping(self):
        identifier = self.submit_and_finish()
        recovered = RecordStore({}, self.root / "experiments").get(identifier)
        self.assertEqual(recovered["status"], "completed")
        self.assertEqual(recovered["runs"], self.store.get(identifier)["runs"])

    def test_timestep_sensitivity_remains_visible_and_provisional(self):
        quality = {"status": "timestep_sensitive", "timestep_relative_change": .118,
            "note": "Exploratory result: timestep refinement changed peak by 11.8%; shortlist is provisional."}
        self.registry["numerical_quality"] = quality
        self.catalog = get_catalog(available=True, numerical_quality=quality)
        identifier = self.submit_and_finish()
        record = self.store.get(identifier)
        self.assertEqual(record["status"], "completed")
        self.assertTrue(record["selection"]["provisional"])
        self.assertIn(quality["note"], record["selection"]["notes"])
        summary = self.client.get(f"/v1/experiments/{identifier}/summary").json()
        self.assertEqual(summary["numerical_quality"], quality)
        self.assertIn(quality["note"], summary["limitations"])
        self.assert_contract(summary, "Summary")

    def test_complete_cache_returns_immediately_without_scheduling(self):
        client = TestClient(create_app(store=self.store, submit=lambda identifier: self.scheduled.append(identifier),
            catalog=lambda: self.catalog, artifact_path=lambda record, name: None,
            resolve_cached=lambda record: try_cached(record, registry=self.registry, runs_root=self.root / "runs")))
        response = client.post("/v1/experiments", json=self.request)
        self.assertEqual(response.status_code, 202)
        record = response.json()
        self.assertEqual(record["status"], "completed")
        self.assertEqual(self.scheduled, [])
        self.assertEqual(self.store.get(record["experiment_id"])["runs"], record["runs"])
        self.assert_contract(record, "Experiment")

    def test_video_byte_ranges_and_artifact_allowlist(self):
        identifier = self.submit_and_finish()
        response = self.client.get(f"/v1/artifacts/{identifier}/firm.mp4", headers={"Range": "bytes=10-19"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.headers["content-range"], "bytes 10-19/100")
        self.assertEqual(response.content, bytes(range(10, 20)))
        self.assertEqual(self.client.get(f"/v1/artifacts/{identifier}/manifest.json").status_code, 404)
        self.assertEqual(self.client.get(f"/v1/experiments/unknown").status_code, 404)
        self.assertIsNone(resolve_artifact(self.store.get(identifier), "../secret", registry=self.registry, root=self.root))

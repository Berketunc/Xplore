"""Frozen v1 HTTP contract. Compute and persistence are injected by Modal."""

from pathlib import Path
import re
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.records import create_record, make_summary


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.0"]
    test_id: str
    candidate_ids: list[str] = Field(min_length=1, max_length=3)
    load_multiplier: FiniteFloat = Field(gt=0)
    target_max_deformation_pct: FiniteFloat = Field(gt=0, le=100)
    prototype_costs_gbp: dict[str, FiniteFloat | None] = Field(default_factory=dict)


def create_app(*, store, submit, catalog, artifact_path, refresh=None, resolve_cached=None):
    app = FastAPI(title="Xplore experiment API", version="1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Range"], expose_headers=["Accept-Ranges", "Content-Range", "Content-Length"])

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, error):
        return JSONResponse(status_code=error.status_code, headers=error.headers, content={"error": {"code": "not_found" if error.status_code == 404 else "invalid_request", "message": str(error.detail), "details": None}})

    @app.exception_handler(Exception)
    async def server_error(request, error):
        return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "The experiment service could not complete this request", "details": None}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Request does not match the experiment contract", "details": [{"location": list(e["loc"]), "message": e["msg"]} for e in error.errors()]}})

    def read_record(identifier):
        if re.fullmatch(r"xplore-[0-9a-f]{32}", identifier) is None:
            raise HTTPException(404, "Experiment not found")
        record = store.get(identifier)
        if record is None:
            raise HTTPException(404, "Experiment not found")
        if refresh:
            record = refresh(record)
        return record

    @app.get("/health")
    def health():
        return {"status": "ok", "schema_version": "1.0"}

    @app.get("/v1/catalog")
    def get_catalog():
        return catalog()

    @app.post("/v1/experiments", status_code=202)
    def create_experiment(body: ExperimentRequest):
        request = body.model_dump()
        tests = {test["test_id"]: test for test in catalog()["tests"]}
        test = tests.get(body.test_id)
        if test is None or test["availability"] != "available":
            raise HTTPException(422, "Test is not available")
        allowed = {candidate["candidate_id"] for candidate in test["candidates"]}
        if len(set(body.candidate_ids)) != len(body.candidate_ids) or not set(body.candidate_ids) <= allowed:
            raise HTTPException(422, "Candidate IDs must be unique entries from the catalog")
        if not set(body.prototype_costs_gbp) <= set(body.candidate_ids) or any(cost is not None and cost < 0 for cost in body.prototype_costs_gbp.values()):
            raise HTTPException(422, "Costs must be nonnegative and refer to requested candidates")
        bounds = test["load"]
        if not bounds["min"] <= body.load_multiplier <= bounds["max"]:
            raise HTTPException(422, "Load multiplier is outside the supported range")
        target = test["target"]
        if not target["min"] <= body.target_max_deformation_pct <= target["max"]:
            raise HTTPException(422, "Deformation target is outside the supported range")
        record = create_record(request, test)
        if resolve_cached:
            cached = resolve_cached(record)
            if cached is not None:
                store.put(cached["experiment_id"], cached)
                return cached
        store.put(record["experiment_id"], record)
        try:
            call_id = submit(record["experiment_id"])
            if call_id:
                store.put("call:" + record["experiment_id"], {"function_call_id": call_id})
        except Exception:
            record["status"] = "failed"
            record["error"] = {"code": "scheduling_failed", "message": "Could not schedule this experiment"}
            store.put(record["experiment_id"], record)
        return record

    @app.get("/v1/experiments/{identifier}")
    def experiment(identifier: str):
        return read_record(identifier)

    @app.get("/v1/experiments/{identifier}/summary")
    def summary(identifier: str):
        record = read_record(identifier)
        test = next(t for t in catalog()["tests"] if t["test_id"] == record["request"]["test_id"])
        return make_summary(record, test)

    @app.get("/v1/artifacts/{identifier}/{filename}")
    def artifact(identifier: str, filename: str):
        record = read_record(identifier)
        path = artifact_path(record, filename)
        if path is None or not Path(path).is_file():
            raise HTTPException(404, "Artifact not found")
        return FileResponse(path)

    @app.get("/v1/examples/{filename}")
    def example(filename: str):
        path = artifact_path(None, filename)
        if path is None or not Path(path).is_file():
            raise HTTPException(404, "Example not found")
        return FileResponse(path)

    return app

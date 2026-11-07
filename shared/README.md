# Shared API contract (FROZEN v1.0)

Drafted by Person A from plan.md §5 and §7 and approved by Person B on 7 Nov 2026. **Person B owns the wire format.** Agree any breaking change together before merging it.

| File | What it is |
| --- | --- |
| `experiment.schema.json` | JSON Schema (2020-12). Each route body is a `$defs` entry: `Health`, `Catalog`, `ExperimentRequest`, `Experiment`, `Summary`, `ApiError`. |
| `catalog.fixture.json` | Example `GET /v1/catalog`. Test is `availability: "proposed"` until the feasibility gate. |
| `experiment.fixture.json` | Example completed `GET /v1/experiments/{id}`. |
| `experiment.partial.fixture.json` | Example `partial` record: one failed candidate, provisional shortlist. |
| `validate.py` | `python3 shared/validate.py` checks all fixtures against the schema. |

All fixtures are `fixture: true`, `evidence_status: "illustrative"`, with `engine`, `execution_mode`, `runtime_seconds` and `video_url` set to `null`. Their numbers are made up for UI development and must never be shown as results.

## Conventions

- `null` means unavailable. Never send placeholder numbers.
- `fixture: true` requires `evidence_status: "illustrative"` (enforced by the schema).
- `engine` is `powersim` or `analytical_baseline`; `null` only for fixtures.
- Candidate result fields stay `null` until that run is `completed`.
- Parent `status`: queued, running, completed, partial, failed. Run `status`: queued, running, completed, failed.
- `selection` is computed by the backend (rule `target-then-cost-v1`, plan §5). The frontend only displays it.
- Errors: 4xx/5xx bodies use `ApiError` (`{"error": {"code", "message", "details"}}`). Use 422 for unsupported IDs and out-of-range loads.

## Open questions for Person B

1. **Metric aggregation:** I proposed `peak` over the full interval. Switch to `settled_mean` if that's more robust for the scene.
2. **Load bounds:** 0.5–2.0 in steps of 0.5 are placeholders until you know the stable range.
3. **Changing only the target or costs:** the frontend will re-POST the same simulation inputs and expects a quick cache hit (new `experiment_id`, runs marked `execution_mode: "cached"`, new `selection`). Does that work, or do you want a dedicated route?
4. **Artifact URLs:** may be relative (`/v1/artifacts/{id}/{file}`). The frontend prefixes the API base URL. MP4 should be H.264 and support byte-range requests.
5. **CORS:** allow `http://localhost:5173` for local development (deployed origin TBD).

# Person A backend handoff

## Live configuration

Use these values in `frontend/.env.local` for the local app:

```dotenv
VITE_API_MODE=live
VITE_API_BASE_URL=https://tnberkec--xplore-simulation-api.us-east.modal.run
VITE_EXAMPLE_EXPERIMENT_ID=xplore-6c8a5838ec8c4202b55abc9725e98ee6
```

These values contain no credentials. Keep provider credentials server-side.
The shared v1.0 schema and existing fixtures are unchanged.

The main frontend has **New experiment**, **Grab and deform** and
**Pillow baseline archive**. New experiments configure a procedural gripper pad or
material block with dimensions and custom stiffness. Live mode opens the pad by
default. The builder and bounded GPU protocol are documented in
[interactive-handoff.md](interactive-handoff.md). Temporary live gestures do not
produce the archive's metrics or rankings. Public frontend hosting is out of scope.

## Actual experiment

- Test ID: `cushion-compression-v1`.
- Display title: **Exploratory pillow compression pulse**.
- One 25,104-particle pillow is isolated from the released scene.
- Lower 15% supported; upper 15% loaded downward for 0.1 simulation seconds;
  gravity off; observe for 2.0 simulation seconds.
- Peak reduction of fixed upper/lower centroid separation, normalized by the
  actual pre-step separation. Fixed IDs, float32 source positions, float64 metric.
- Flexible / Balanced / Firm: 0.5× / 1× / 2× baseline stiffness. Other settings match.
- Only load multiplier **1.0** is enabled; use the live catalog for controls.
- Default target **15%**. With example cost assumptions £2/£3/£5, Balanced is the
  lowest-cost qualifying candidate at these numerical settings. These are example
  user-entered prototype costs, not measured material prices.

## Required evidence wording

The results are real PowerSim runs and `fixture: false`, with
`evidence_status: simulation_only`. They are **exploratory**, not numerically
converged: Balanced is 12.4121% at dt 0.001 and 10.9498% at dt 0.0005, an 11.8%
relative change. The 5% convergence goal was not met. Physical validation is pending.

Keep the catalog's scene description and first assumption visible. The existing
`selection.provisional` flag is true for this test even when every candidate
completes, because numerical sensitivity is unresolved. `selection.notes`,
`experiment.numerical_quality`, and the summary carry the exact reason. A
provisional flag does not necessarily mean a candidate failed.

The saved example omits costs, so it has a qualifying set and no automatic cost
winner. Enter costs and resubmit to demonstrate the deterministic cost shortlist.

## Endpoints and behavior

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Status and schema version |
| `GET /v1/catalog` | Authoritative controls, actual protocol and assumptions |
| `POST /v1/experiments` | HTTP 202; full cache hits may already be completed, otherwise poll by ID |
| `GET /v1/experiments/{id}` | Durable queued/running/completed/partial/failed record |
| `GET /v1/experiments/{id}/summary` | Read-only assistant context, including numerical warning |
| `GET /v1/artifacts/{id}/{filename}` | Approved MP4, PNG, JSON or CSV only |
| `GET /v1/examples/example.json` | Genuine completed cached example |

Poll every two seconds and stop on terminal states. Re-POSTing different costs
or targets creates a new experiment ID and reuses the same physics cache keys.
Runs report `execution_mode: cached` for reuse, with original runtime preserved.

MP4s use H.264, yuv420p, faststart, 448×448 and 50 fps. They have 101 frames: the
unloaded frame at t=0 and samples through t=2.0. The 2.02-second file includes a
normal one-frame hold at the end. Browser range requests are supported.

Artifact URLs are relative and the existing live client can prefix the base URL.
Besides each run's video and still URLs, `artifact_urls` links measurements,
CSV, fixed groups, applied config and state-export metadata. Download the full
record at `/v1/artifacts/{id}/experiment.json`.

CORS permits the frontend origin without cookies or provider credentials. Invalid
IDs, duplicate candidates and unsupported loads are rejected before any GPU work.
Only registered simulation inputs can recover a missing cache; recovery is
claimed once per candidate to bound GPU use.

## Result summaries

The summary endpoint remains available for the archived recorded experiments.
AI/voice integration has been dropped; the frontend retains its deterministic
record-based explanation.

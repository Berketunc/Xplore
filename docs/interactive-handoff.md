# Live mouse interaction

The main frontend now opens **Grab and deform** in live mode. A saved experiment
URL opens **Recorded comparison** instead, and the fixture-only mock mode retains
the comparison screen. Person B integrated the live workspace at the user's
request; Person A's experiment setup/results flow remains available in its tab.

Direct workspace: https://tnberkec--xplore-simulation-api.us-east.modal.run/sandbox

Use the live configuration in [api-handoff.md](api-handoff.md). The frontend
embeds the backend-hosted workspace so that its HTTP and WebSocket connections
share an origin. Opening the workspace or orbiting its static object uses no GPU.
Press **Start live physics**, wait for readiness, then left-drag the upper pillow
to grab, push or pull it. Release the pointer to release the simulated constraint.
Right-drag orbits; scrolling zooms. Reset restores the initial particle state.
Choose another stiffness before starting a new session.

## What actually runs

The remote worker uses PowerSim's bundled PhysGaussian MPM solver and the same
25,104-particle isolated pillow reference as the recorded comparison. Gravity and
the recorded compression pulse are disabled. The original lower support stays
fixed. Mouse grabbing adds a velocity constraint to particles within 0.08 MPM
units of the nearest particle to the clicked surface point, excluding support
particles. Target displacement is limited to 0.25 units and grab speed to 0.5
units per simulation second. Flexible/Balanced/Firm set E to 5,000/10,000/20,000.
The common substep is 0.001; each streamed update advances 33 substeps.

Three.js draws a 207-vertex convex surface proxy whose vertices follow actual
solver particles. It does not run a separate browser soft-body model or replay
the recorded videos. The proxy is less detailed than PowerSim's neural render
and does not preserve interior surfaces or concavities. Coordinates are normalized
simulator units, not calibrated physical lengths. Physical agreement and numerical
convergence for interactive gestures have not been established.

Live gestures are temporary and independent of recorded experiment metrics,
rankings and saved videos. They currently do not create a saved experiment record.
Use Recorded comparison for the repeatable pulse protocol and provisional shortlist.

## HTTP and WebSocket contract

| Route | Purpose |
| --- | --- |
| `GET /sandbox` | Self-contained browser workspace |
| `GET /v1/interactive/mesh` | Static mesh, topology and support IDs; no GPU |
| `POST /v1/interactive/sessions` | Reserve a bounded session with `{"candidate_id":"balanced"}` |
| `WS /v1/interactive/sessions/{session_id}/stream` | Commands in, solver surface updates out |

A session response provides `session_id`, relative `websocket_url`,
`max_live_seconds` and `remaining_starts`. Valid candidates are `flexible`,
`balanced` and `firm`. IDs expire 180 seconds after reservation and can join once.

Commands:

```json
{"type":"grab","point":[1.0,1.0,1.3],"target":[1.0,1.0,1.3]}
{"type":"move","target":[1.0,1.0,1.2]}
{"type":"release"}
{"type":"reset"}
{"type":"stop"}
```

Coordinates must be three finite numbers within [0.15, 1.85]. Move commands are
limited to 40 per second at the API. The worker aims for 30 streamed updates per
second. Packets are `loading`, `ready` (mesh/candidate/limit), `frame` (flat xyz
positions, sequence, simulation time, remaining seconds), `ended` or `error`.
The recorded experiment's frozen v1.0 contract remains unchanged.

## Resource limits and startup

Only one interactive worker can be active. The persistent allowance is **20
session reservations total**, including development checks and failed startups;
redeploying does not reset it. Busy sessions return HTTP 409 and exhaustion 429.
Each session has at most 90 live seconds, a 180-second worker timeout, no retries,
and 30 seconds of idle retention. Stop/disconnect forwards a stop command. The
public API exposes no provider credentials or arbitrary code/configuration.

GPU allocation falls back across L4, L40S, A10 and T4. Initial allocation and Warp
kernel compilation can take about a minute; a 100-second readiness deadline gives
a visible failure if capacity is unavailable. Compiled kernels persist on the
Volume for subsequent starts. These are application limits, not a provider-wide
account spending cap. Usage snapshots can lag actual usage.

## Verification

The deployed native WebSocket checks passed non-rigid deformation, finite state,
release, reset and stop for all three options:

| Candidate | Startup | Received updates/s | First movement after grab |
| --- | --- | --- | --- |
| Flexible | 59.49 s | 30.37 | 0.530 s |
| Balanced | 73.81 s | 28.57 | 0.315 s |
| Firm | 1.57 s (warm worker) | 32.38 | 0.421 s |

Raw results are in `interactive-verification.json`,
`interactive-verification-flexible.json` and `interactive-verification-firm.json`.
These are native WebSocket measurements, not browser rendering or input-latency
benchmarks. The isolated physics benchmark in
`interactive-benchmark-result.json` uses 10 substeps/update and excludes network
streaming; its throughput should not be presented as browser frame rate.

Run a bounded deployed check (consumes one reservation and GPU time):

```sh
backend/.venv/bin/python scripts/verify_interactive.py https://tnberkec--xplore-simulation-api.us-east.modal.run
```

The frontend passes TypeScript checking and the production build. Browser visual
inspection remains outstanding; no Chrome extension or computer-use permission
is needed for the workspace itself. WebGL and access to the pinned Three.js CDN
are required in the user's browser.

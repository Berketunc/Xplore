# Local robotics material workspace

The primary demo is a **silicone-inspired robot gripper pad**, created procedurally
and simulated by PowerSim's bundled PhysGaussian MPM solver. The older pillow
compression comparison remains in **Pillow baseline archive**. Its measurements
are not gripper-pad results.

## Launch and create a test

Run the frontend locally with the live settings in [api-handoff.md](api-handoff.md):

```sh
cd frontend
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173/ and click **+ New experiment**. Choose **Robot gripper
pad** or **Material test block**. Set width, depth, thickness and material stiffness.
The 3D preview updates without starting a GPU session. Press **Start live physics**,
wait for readiness, then drag the free surface to press or stretch it. Release the
pointer to release the constraint; Reset restores the original specimen with the
same dimensions and material. New experiment returns to a fresh gripper-pad setup.
Right-drag orbits and scrolling zooms. The dark base is the fixed mounting layer.

The UI runs locally; Modal still supplies remote GPU physics, so internet access
is required. Public frontend hosting, AI/voice, and saving mouse experiments have
been explicitly removed from scope. Live settings and gestures are temporary.
The baseline archive retains its existing recorded comparison results and exports.

## Object and material bounds

| Setting | Supported range | Default pad |
| --- | --- | --- |
| Width | 0.5–1.1 | 1.0 |
| Depth | 0.3–0.9 | 0.6 |
| Thickness | 0.16–0.6 | 0.25 |
| Stiffness multiplier | 0.5–2.0 | 1.0 |

Dimensions are relative simulator units, not millimetres. The block preset defaults
to 0.6 in each dimension. Material options provide 0.5×/1×/2× or custom stiffness
within those bounds. This is a bounded procedural specimen builder; arbitrary
CAD/object uploads and commercial-material calibration are outside this build.

Silicone is used in soft robotics, including the Dragon Skin silicone actuators
shown in the [Soft Robotics Toolkit](https://softroboticstoolkit.com/book/pneunets-bill-materials).
That motivates the application; it does not calibrate this model. The simulation
uses a generic fixed-corotated elastic law, E = 10,000 times the selected stiffness,
Poisson ratio 0.3 and density 2,000 in simulator conventions. These are hypothetical
parameter scenarios, not measured properties of Ecoflex or Dragon Skin. Manufacturer
hardness and 100%-strain modulus are not silently treated as Young's modulus.
Physical agreement and numerical convergence have not been established.

## Geometry and physics

`backend/geometry.py` generates a deterministic Cartesian lattice at spacing no
greater than 0.025 units. Tensor-product trapezoidal nodal volumes sum to the exact
cuboid volume. The default pad has 11,275 physics particles. The browser draws a
closed 802-vertex structured surface sampled from those actual particles; each
face contains interior surface vertices so a local indentation can be displayed.
Preview and GPU worker use the same geometry/configuration code and particle IDs.
No neural checkpoint, pillow geometry, replay clip or browser soft-body solver is
used for the live pad.

The lower 15% of initial specimen height is fixed by grid/particle velocity
constraints. Gravity is off. A grab selects nearby particles within 0.08 units,
excluding the supported group. Target movement is capped at the smaller of 0.25
units and 40% of specimen thickness; speed is capped at 0.5 units/s. The common
substep is 0.001 and each streamed update advances 33 substeps. Changes in geometry
or material settings generate a fresh solver when the next session starts.

Mouse dragging is an imposed local motion constraint. It does not measure contact
force, friction, grip security, pressure actuation, fatigue or damage. No saved
ranking or quantitative screening result is generated from these temporary tests.

## HTTP and WebSocket protocol

| Route | Purpose |
| --- | --- |
| `GET /sandbox` | Backend-hosted workspace embedded by the local frontend |
| `GET /v1/interactive/mesh` | Default pad preview; no GPU |
| `POST /v1/interactive/preview` | Configured mesh and metadata; no session allowance consumed |
| `POST /v1/interactive/sessions` | Reserve a bounded GPU session with the same configuration |
| `WS /v1/interactive/sessions/{session_id}/stream` | Commands in, actual solver surface updates out |

Preview/session request example:

```json
{"object_type":"gripper_pad","width":1.0,"depth":0.6,"thickness":0.25,"candidate_id":"balanced","stiffness_multiplier":1.2}
```

Objects are `gripper_pad` and `material_block`. Candidate IDs remain `flexible`,
`balanced` and `firm`; an explicit stiffness multiplier overrides their default.
Unsupported objects, nonfinite values and out-of-range dimensions/stiffness are
rejected before a session is reserved. Responses include the resolved configuration.

WebSocket commands are unchanged:

```json
{"type":"grab","point":[1.0,1.0,1.125],"target":[1.0,1.0,1.125]}
{"type":"move","target":[1.0,1.0,1.08]}
{"type":"release"}
{"type":"reset"}
{"type":"stop"}
```

Coordinates must be finite triples within [0.15, 1.85]. API move commands are
limited to 40/s; the worker aims for 30 updates/s. Packets are loading, ready
(mesh/configuration), frame (positions, sequence, simulation time, remaining
seconds), ended or error. The archived experiment's frozen v1.0 schema is unchanged.

## Limits and evidence

Only one live worker can run at a time. Each session allows 90 live seconds, a
180-second worker timeout and 30 seconds of idle retention. There are 20 total
session reservations in the persistent allowance, including development checks
and failed startups; redeploying does not reset it. Busy returns 409 and exhausted
allowance 429. Previewing and editing geometry do not reserve a GPU session.

GPU allocation falls back across L4/L40S/A10/T4. Initial allocation/kernel
compilation can take about a minute; a 100-second readiness deadline gives a
visible failure if capacity is unavailable. Application limits are not a provider
account spending cap. Usage snapshots may lag actual usage.

`robotics-verification-gripper_pad-balanced.json` records a genuine deployed pad
session: matching CPU/GPU configuration, non-rigid pressing, finite positions,
release, reset and stop. Additional checks passed for the firmest material on the
thinnest allowed pad (`robotics-verification-gripper_pad-firm.json`) and a new
0.8 × 0.5 × 0.4 block at custom stiffness 1.3×
(`robotics-verification-material_block-balanced.json`). The latter verifies that
a new object/material configuration reaches the real solver and survives reset.
The older `interactive-verification*.json` and isolated
`interactive-benchmark-result.json` files describe historical pillow tests and
must not be presented as pad benchmarks. Native WebSocket results do not measure
browser rendering or pointer-event latency.

Run a bounded deployed check (consumes one GPU reservation):

```sh
backend/.venv/bin/python scripts/verify_interactive.py https://tnberkec--xplore-simulation-api.us-east.modal.run
```

Thirty local tests cover the archived API/metrics, commands, session bounds,
configuration validation, exact volume, closed outward-wound surface topology,
and propagation of geometry/material settings. The user confirmed that the prior
pillow browser workspace worked. A fresh browser check is needed for the changed
pad/builder; we have not used computer automation to claim otherwise. WebGL and
access to the pinned Three.js CDN are required.

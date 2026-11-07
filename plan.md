# Xplore: Virtual Material Experiments

> Implementation update, 7 November 2026: the user clarified that direct mouse
> grabbing, pushing and deformation is the primary interaction. The live frontend
> now opens that GPU-backed workspace and retains the repeatable experiment flow
> in a Recorded comparison tab. Person B also integrated this frontend workspace
> at the user's request. See [the live interaction handoff](docs/interactive-handoff.md)
> and [current evidence](docs/validation.md). The sections below preserve the
> original plan; live gestures currently are temporary and do not create saved
> comparison metrics. Numerical and physical validation remain incomplete.

## 1. Project summary

**Xplore helps small product design teams compare soft-material options virtually and decide which prototypes to physically test next.**

The first use case is a cushioning product for protective packaging. A designer selects one prepared object, compares three material parameter sets under the same loading conditions, and receives visual results, a quantitative comparison, and an explanation of the tradeoffs.

The impact hypothesis is that early virtual screening can reduce unnecessary prototype iterations, material consumption, and experiment turnaround time. The hackathon will demonstrate the screening workflow and report the evidence actually collected. Commercial savings remain a hypothesis until measured with users.

**Project name:** Xplore  
**Team:** Person A and Person B  
**Primary audience:** Small product design teams and makers developing soft cushioning products  
**Hackathon target:** Overall impact competition  
**Initial scope:** One prepared object, one experiment type, three candidate parameter sets  
**Compute:** MacBooks for development and the browser; Modal for remote NVIDIA GPU computation  
**Simulation:** PowerSim, with a clearly identified analytical fallback if GPU integration fails

**Pitch:** "Xplore helps small design teams compare material options before committing their physical testing budget to the most promising prototypes."

This is the manufacturing and virtual experimentation direction selected in the conversation. A learning mode is a future extension of the same experiment engine.

## 2. The problem and intended outcome

### User problem

A small design team has a cushioning concept and several possible material choices. They need to understand how the choices change deformation under a specified load. Producing and testing every option may consume time, materials, and budget before the team has a useful shortlist.

### What Xplore provides

1. A repeatable experiment setup with explicit assumptions.
2. Comparable simulations using the same geometry and loading protocol.
3. A visual and numerical comparison of material scenarios.
4. A shortlist based on a user-selected deformation target and optional user-provided prototype costs.
5. A plain-language explanation of the results and a suggested next physical experiment.
6. A reproducible experiment record containing inputs, results, engine version, and evidence status.

### The decision being supported

"Which candidate should we physically test next under this specific deformation constraint?"

A candidate meeting that simulated constraint is a screening result. Real cushioning performance also depends on factors such as transmitted force, energy absorption, recovery, and repeated loading. These broader performance criteria require additional models and experiments.

### What makes the project distinctive

The contribution is the accessible experiment workflow around a research simulator: consistent comparisons, traceable measurements, explicit assumptions, and an assistant grounded in actual experiment results. Attribute the underlying simulation method and released assets to their original authors.

## 3. Success criteria and scope

### P0: Required for the hackathon

- [ ] A browser application branded Xplore.
- [ ] One prepared scene and one supported loading protocol.
- [ ] Three candidate parameter sets applied to the same object.
- [ ] A real simulation result for every displayed candidate.
- [ ] A documented deformation metric calculated from simulation state.
- [ ] A comparison table and synchronized or manually aligned result videos.
- [ ] A deterministic shortlist with an explanation of its selection rule.
- [ ] Visible assumptions and evidence status.
- [ ] Correct handling of queued, running, completed, and failed jobs.
- [ ] A reusable saved experiment and a genuine cached example for the demo.
- [ ] A deployed app, repository, write-up, and submission video.

### P1: Add after the full P0 flow works

- [ ] An AI assistant that retrieves the experiment record before explaining it.
- [ ] ElevenLabs spoken explanations with an equivalent visible text explanation.
- [ ] JSON/CSV export of inputs, measurements, assumptions, and results.
- [ ] A second load setting to demonstrate a meaningful change in outcomes.
- [ ] A matched physical validation experiment, if the geometry and loading can be reproduced properly.

### P2: Future work

- Custom object reconstruction and a general CAD import pipeline.
- Material parameter inference from user-recorded deformation videos.
- Material datasheet ingestion and provenance through Firecrawl.
- More constitutive models, objective functions, and experiment types.
- n8n workflows for experiment reports and team notifications.
- An educational mode that adds predictions, explanations, and learning checks.

### Scope boundaries for this build

Use a prepared scene. Keep object reconstruction, arbitrary uploads, broad material discovery, and unrestricted simulation settings outside the hackathon critical path. Advanced manufacturing claims such as fatigue life, fracture prediction, or qualification for production are outside the evidence this prototype will establish.

## 4. The demonstration experiment

### Preferred setup

Use one soft cushioning object, with compression as the preferred experiment. Candidate scenarios vary stiffness while retaining the same geometry, density, Poisson's ratio, supports, load protocol, camera, duration, and numerical settings. Label them as parameter scenarios until actual material properties are sourced and validated.

The released PowerSim download script lists a pillow asset. Person B should investigate whether that asset and the available configurations support a useful experiment. Asset availability alone does not establish a ready-made compression test. Download only the chosen scene initially. [PowerSim download script](https://github.com/nttung1110/PowerSim/blob/main/scripts/download_checkpoints.py)

### Scene selection gate

By the first feasibility checkpoint, Person B must establish:

1. Which released scene runs successfully.
2. Which loading protocol can actually be implemented with it.
3. Which quantitative metric the state export supports.
4. Whether the scene is illustrative or dimensionally calibrated.

If compression requires excessive custom geometry or boundary-condition work, use a supported deflection experiment on a prepared deformable object. Change the experiment title, metric, and claims together. Preserve the Xplore comparison workflow.

### Candidate definitions

Start with three hypothetical scenarios named Flexible, Balanced, and Firm. These are interface labels, not verified commercial material grades.

Person B chooses numerically stable stiffness settings around a working baseline. Multipliers such as 0.5, 1.0, and 2.0 are an initial experiment proposal, subject to numerical checks. Keep every other variable fixed in the first comparison. If the numerical integration requires a smaller timestep for a stiffer scenario, rerun all candidates with the same suitable timestep.

Actual material names require a source, units, a suitable constitutive model, and a mapping to the simulator's dimensional assumptions. The assistant must retain these distinctions.

### Main user journey

1. The designer opens the prepared cushioning experiment.
2. They select three candidates and a supported load multiplier.
3. They enter a maximum allowed normalized deformation and optional prototype costs.
4. They start the comparison.
5. Xplore displays job states and then the result videos and measured deformation.
6. It identifies candidates that meet the stated simulation target.
7. Among qualifying candidates with complete cost data, it highlights the lowest user-provided prototype cost.
8. The assistant explains the tradeoff using the experiment record.
9. The designer saves the record and selects the next physical test.

If no candidate meets the constraint, show that outcome and suggest a bounded follow-up experiment. Avoid manufacturing an automatic winner.

## 5. Evidence, measurements, and physical meaning

### Evidence status

Every experiment must carry one of these states:

| Status | Meaning | UI wording |
| --- | --- | --- |
| simulation_only | A real simulation with stated assumptions; physical agreement has not been established | Simulation result; physical validation pending |
| physically_compared | A matching physical experiment has been compared with the prediction; measured error and conditions are available | Compared with a physical experiment |
| illustrative | A development fixture or simplified illustration | Illustrative preview |

Store engine identity separately: powersim or analytical_baseline. A cached PowerSim run retains its engine identity and adds a cached execution label. A development fixture must not acquire simulation_only status merely because the interface looks complete.

### Units and calibration

Default to relative, dimensionless reporting for released scenes whose physical scale and force interpretation have not been established. Use labels such as "load multiplier" and "deformation as a percentage of reference length."

Person B must establish consistent length, mass/density, time, force, and material-property units before the UI reports physical predictions in mm or N. Measuring a displayed object's apparent length alone does not establish dimensional calibration of the entire solver.

The PowerSim paper describes material recovery as dependent on assumptions about density, scale, and boundary conditions. Treat material identification and manufacturing accuracy as validation tasks. [PowerSim paper, discussion](https://arxiv.org/html/2609.38153v1#S6)

### Deformation metric

Freeze exactly one primary metric with the chosen loading protocol:

- **Compression:** Define fixed upper and lower particle groups at the unloaded state. Track the separation of their centroids along the loading axis. Compression percentage is 100 times the reduction in separation divided by the initial separation.
- **Deflection fallback:** Define a fixed region of interest and fixed support group at the unloaded state. Track the region's mean displacement relative to the support group along the loading axis, normalized by a declared initial reference length.

For either metric, declare whether the reported value is the peak over a fixed interval or the mean over a predefined settling window. Use the same rule and duration for every candidate. Save the full time series. Geometry-based displacement is the metric; conclusions about protective performance require further evidence.

PowerSim exposes per-frame positions, but the existing export occurs after stepping and uses float16. Person B should add a minimal export adapter or patch to save an actual unloaded baseline, stable particle IDs, region membership, timestep metadata, and sufficient precision for the selected metric. Record the patch in the repository. [Simulation source](https://github.com/nttung1110/PowerSim/blob/main/powersim/foam_evolve/simulate.py)

### Deterministic selection rule

1. Exclude failed or incomplete candidates from a definitive recommendation.
2. Mark each completed candidate as meets_target or exceeds_target according to the declared metric and threshold.
3. When all relevant costs are supplied, order qualifying candidates by user-provided prototype cost; break ties by lower deformation, then stable candidate ID.
4. When costs are incomplete, show the deformation comparison and explain that a complete cost ranking is unavailable.
5. If any requested candidate failed, describe any shortlist as provisional.

The backend calculates these decisions. The assistant explains them. It may suggest another supported experiment but may not change the rule or invent measurements.

### Impact metrics

Report measured evidence separately from future benefits:

| Metric | How to collect it | Owner |
| --- | --- | --- |
| Time to compare three scenarios | Measure browser submission to completed results; report cached and new runs separately | B |
| Simulation compute cost | Use actual platform usage or measured runtime and a recorded applicable rate | B |
| Physical prediction error | Compare a matching specimen and held-out loading condition | B, with A recording |
| Decision usefulness | Ask 2-3 willing design/engineering participants to use the result and describe their next test | A |
| Potential prototype savings | Use an explicitly labelled scenario with user-provided assumptions | A |

Do not report a percentage of material waste or time saved as an observed outcome without a real baseline comparison.

## 6. Architecture and technology choices

~~~mermaid
flowchart LR
    U[Designer using a MacBook browser] --> F[Xplore frontend]
    F --> API[Experiment API on Modal CPU]
    API --> Q[Background job]
    Q --> GPU[PowerSim on Modal NVIDIA GPU]
    GPU --> STORE[Artifacts and experiment records]
    STORE --> API
    API --> F
    AGENT[Optional ElevenLabs agent] -->|Read experiment summary| API
    AGENT --> F
~~~

### Components

| Component | Choice | Purpose | Owner |
| --- | --- | --- | --- |
| Browser app | Lovable-generated React/TypeScript, edited locally as needed | Setup, results, assumptions, saved example | A |
| API | FastAPI on Modal CPU | Validate input, submit jobs, return state and artifacts | B |
| Worker | PowerSim in a pinned Linux CUDA environment on Modal | Execute approved experiments | B |
| Storage | Modal Volume plus an HTTP artifact route | Checkpoints, manifests, results, browser-readable videos | B |
| Assistant | ElevenLabs agent with a read-only experiment tool, if available | Explain measured results | A; B supplies tool endpoint |
| Data contract | JSON fixtures plus shared schema | Allow A and B to work independently | Joint; B owns wire format |

Modal supports remote CUDA computation and asynchronous job submission with polling. Store persistent data separately from transient workers. The browser receives an experiment ID immediately and polls for updates. [CUDA](https://modal.com/docs/guide/cuda), [job processing](https://modal.com/docs/guide/job-queue), [Volumes](https://modal.com/docs/guide/volumes)

### API priorities

- Modal, PowerSim, and the frontend are the core stack.
- ElevenLabs is the first optional integration once real results flow end to end.
- Firecrawl, n8n, and Yubico are future integrations unless a finished core leaves clear time for a specific useful addition.

### GPU setup

Person B verifies GPU access and available credit first. Modal's documentation currently requires a valid payment method for GPU use; confirm the hackathon account arrangement. Start with one available GPU, initially an L40S if accessible, and benchmark memory and runtime before optimizing cost. Hardware choice is provisional. [Modal GPU guide](https://modal.com/docs/guide/gpu)

Match PowerSim's published environment initially: Python 3.11 and CUDA 12.8-oriented dependencies. Pin the upstream commit used for the build. Keep changes to numerical and export behavior small and recorded. [PowerSim dependencies](https://github.com/nttung1110/PowerSim/blob/main/requirements.txt)

### Cost and execution controls

- Start with one GPU worker and serial candidate execution.
- Cap every experiment at three approved candidates.
- Permit only catalogued scenes, controls, and bounded load values.
- Set a per-run timeout after the first benchmark; an initial ten-minute cap is a planning ceiling, not a performance promise.
- Cache by all simulation-relevant inputs and versions.
- Keep checkpoints persistent so normal runs do not repeatedly download them.
- Separate GPU execution time, queue delay, and rendering time in logs.
- Record the credit allowance and a working spend ceiling before running a batch.

## 7. Shared API contract

Freeze the first contract before building independent UI and worker implementations. Person A uses fixtures with exactly the same structure until the API is available.

### Routes

| Method and route | Responsibility | Minimum response |
| --- | --- | --- |
| GET /health | Basic API availability | Status and schema version |
| GET /v1/catalog | Supported scene, protocol, candidates, bounds, units | Catalog JSON |
| POST /v1/experiments | Validate and schedule a comparison | HTTP 202, experiment ID, queued status |
| GET /v1/experiments/{id} | Read state and results | Status, candidate runs, measurements, assumptions |
| GET /v1/experiments/{id}/summary | Compact read-only assistant context | Results, selection rule, evidence state |
| GET /v1/artifacts/{id}/{filename} | Serve an approved result file | Video, image, JSON, or CSV |

The catalog is authoritative. Compression is exposed only after it works. If the supported protocol is deflection, the catalog and UI must describe deflection consistently.

### Proposed request fixture

This is a schema example, not evidence that the scene already exists. Replace the proposed test ID with the registered working experiment at the first feasibility gate.

~~~json
{
  "schema_version": "1.0",
  "test_id": "cushion-compression-v1",
  "candidate_ids": ["flexible", "balanced", "firm"],
  "load_multiplier": 1.0,
  "target_max_deformation_pct": 20.0,
  "prototype_costs_gbp": {
    "flexible": 2.0,
    "balanced": 3.0,
    "firm": 5.0
  }
}
~~~

### Proposed queued response

~~~json
{
  "schema_version": "1.0",
  "experiment_id": "xplore-example",
  "status": "queued",
  "completed_runs": 0,
  "total_runs": 3,
  "runs": [],
  "selection": null,
  "evidence_status": "simulation_only"
}
~~~

### Completed run fields

Each run includes candidate_id, status, engine, execution_mode, cache_key, metric_id, deformation_pct, time_series, video_url, runtime_seconds, and error. Results are null until available. execution_mode is live or cached. Runtime values always describe the actual execution being reported.

The parent record includes the validated request, unit_system, assumptions, evidence_status, selection, created_at, completed_at, code versions, checkpoint identity, config hash, and artifact references. Add physical_validation only when the associated records exist.

Use null for unavailable measurements. Illustrative fixtures use evidence_status illustrative and an explicit fixture flag. The frontend must not substitute sample numbers for missing real results.

### Job behavior

- Parent states: queued, running, completed, partial, failed.
- Candidate states: queued, running, completed, failed.
- Status is durable across different API worker instances; avoid relying on process-local memory.
- Poll approximately every two seconds and stop after a terminal state. Restore a saved experiment by ID after refresh.
- Show completed candidate count. Avoid invented percentage progress when the worker cannot report it.
- Repeated submissions with identical simulation inputs reuse a job or cache entry. Display-only changes such as costs or target threshold can recompute the shortlist without rerunning physics.
- Validate ranges and IDs server-side. Use a separate per-run directory and cache key for each candidate.
- Keep provider credentials server-side; give the browser only the access needed to use the application.
- Restrict artifact routes to known experiment files. Verify browser playback and any required byte-range handling.

## 8. Work ownership

**Person A owns the product interface, assistant experience, user evidence, and presentation. Person B owns simulation, cloud execution, measurements, and the API.**

The critical handoff is the API contract. The first integration milestone is one real result appearing in the frontend. Keep shared-file changes explicit so work does not collide.

### Person A: Detailed tasks

| ID | Task | Deliverable and completion condition | Dependency |
| --- | --- | --- | --- |
| A1 | Set up Xplore frontend and visual identity | App opens locally with Xplore name, clear purpose, and one experiment entry point | None |
| A2 | Build setup and fixture-driven results | Scene summary, three candidates, load control, constraint, cost fields, and comparison render from shared fixtures | Contract agreed |
| A3 | Build asynchronous states | Queued, running, failed, partial, and completed screens work; duplicate run clicks are prevented | Fixtures |
| A4 | Connect the real API | A browser-submitted experiment shows one genuine returned video and metric | B4 |
| A5 | Complete comparison and explanation | Real three-candidate data, target labels, assumptions, cached label, and deterministic explanation are visible | B3/B4 |
| A6 | Add the optional ElevenLabs assistant | Agent retrieves the current experiment summary and explains it; text path remains usable | Stable summary endpoint and account access |
| A7 | Collect user evidence and record footage | Two or three short user observations if available; optional matched-test footage | Working interaction |
| A8 | Deploy and package the project | Published frontend, screenshots, two-minute video, write-up, and submission metadata | Working P0 |

**First actions for Person A**

1. Confirm team/project registration and challenge selections before the published 13:30 soft deadline, if still pending.
2. Start the frontend from the agreed fixture immediately; do not wait for the GPU environment.
3. Build the complete setup-to-results journey with visible illustrative labels while using fixtures.
4. Ask a nearby maker or engineering participant what result would help them choose a next prototype; use that feedback to tighten copy and the target constraint.

### Person B: Detailed tasks

| ID | Task | Deliverable and completion condition | Dependency |
| --- | --- | --- | --- |
| B1 | Verify Modal and build environment | Remote worker sees an NVIDIA GPU and imports the required simulation packages | Account access |
| B2 | Reproduce and select an experiment | One released scene produces a valid result; loading, metric, and scope are frozen | B1 |
| B3 | Implement candidate runner and measurements | Three stable scenarios, unloaded baseline, time series, comparable metrics, manifest, and videos | B2 |
| B4 | Implement API and persistent job state | Catalog, submit, polling, artifact, and summary routes satisfy the contract | Contract; B2 for live data |
| B5 | Benchmark and cache genuine results | Runtime/memory evidence, bounded execution, versioned cache, and one saved example | B3/B4 |
| B6 | Run optional physical comparison | Matched geometry/loading, calibration record, and held-out error; otherwise validation remains pending | Suitable specimen and time |
| B7 | Final reliability and attribution | Deployed backend, reproducible command/config, citations, license notes, and demo-ready artifacts | B3-B5 |

**First actions for Person B**

1. Verify GPU access before downloading large assets.
2. Fetch the upstream source at a recorded commit and inspect the released scripts/configurations.
3. Download one promising scene. Attempt the existing reproduction before modifying loading or material settings.
4. Tell Person A which scene and experiment actually work as soon as known.

### Joint checkpoints

- Agree contract, initial metric, and fixture semantics at the beginning.
- At the first feasibility gate, freeze the supported scene and loading protocol.
- Integrate one real candidate before polishing optional features.
- Review the shortlist against raw results together.
- Rehearse one full demo together using the exact deployed application.

## 9. Hackathon schedule

Plan prepared on **7 November 2026, approximately 13:05 Europe/London (GMT)**. The schedule below targets a 13:15 working start and a 17:30 submission buffer. If work begins later, shorten optional work first. The published final submission deadline is 18:00; the dashboard soft deadline is 13:30. [Event schedule](https://greatunihack.com/)

| Time, GMT | Person A | Person B | Required outcome |
| --- | --- | --- | --- |
| 13:15-13:30 | Registration check, app scaffold, fixture contract | GPU access, source inspection, environment setup | Contract frozen; downloads/build started |
| 13:30-14:00 | Setup/results interface with fixtures | Reproduce one released scene | Gate 1: a real baseline or a clear fallback decision |
| 14:00-14:45 | State handling, comparison UI, API client | Freeze loading/metric, export baseline, run first variants | Gate 2: one genuine metric and playable clip |
| 14:45-15:15 | Integrate live API | Submit/poll/artifact routes, persistent state | Browser-to-result flow works |
| 15:15-16:00 | Complete comparison, gather quick user feedback | Three candidates, numeric checks, cache, optional matched-test preparation | Gate 3: complete P0 journey |
| 16:00-16:30 | Assistant or voice if ready; otherwise polish core | Physical comparison if feasible; otherwise benchmark and stability | Evidence and claims frozen |
| 16:30-17:00 | Deploy, record application footage, write submission | Final backend deployment, export artifacts and source attribution | Feature freeze; demo-ready version |
| 17:00-17:30 | Assemble video, publish required video link, submit | Rehearse, verify deployment, assist final submission | Target submission complete |
| 17:30-18:00 | Fix submission or access issues only | Fix blocking deployment issues only | Final deadline buffer |

The public submission requirements include a repository, both team members, selected tracks, a project description, and a demo video of at most two minutes supplied as a YouTube link. [Submission requirements](https://greatunihack-2026.devpost.com/)

## 10. Simulation implementation sequence

### Stage 1: Establish a working baseline

Person B builds a Modal environment, runs one released example, and saves its exact source revision, asset identity, config, and runtime. Keep the released scene intact during this first reproduction. A successful baseline means an actual output clip opens and the underlying simulation state is finite.

### Stage 2: Establish controlled variants

Wrap the simulator with a small application-owned runner. It receives approved candidate IDs, constructs isolated configs, executes each candidate, and writes a result manifest. Confirm that the selected material assignment path changes the intended properties: a spatial material field can override scalar config values. Pin or deliberately update that field when comparing candidates. [Material handling](https://github.com/nttung1110/PowerSim/blob/main/powersim/foam_evolve/simulate.py)

### Stage 3: Measure the simulation

Implement the baseline and region exports described in section 5. Compute the agreed metric from numerical state. Preserve the loading axis and particle selection across candidates. Save measurements before generating any explanation. Use the same sampling interval for chart/video alignment.

### Stage 4: Produce browser-ready artifacts

Write a manifest, time-series JSON/CSV, still image, and MP4 for each completed candidate. Persist them before returning a completed state. Provide browser-readable HTTP artifact URLs through the application backend; a storage volume path by itself is not a browser URL.

### Stage 5: Cache and replay

Build a cache key from scene/checkpoint identity, material assignment, load protocol, numerical settings, camera/render settings, upstream commit, and Xplore runner version. Include any random seed that affects the result. Display a cached result immediately when the key matches, while retaining its actual execution metadata.

## 11. Assistant behavior

The assistant's useful task is explaining a reproducible experiment and helping the designer choose the next supported test.

### Minimum behavior

Person A can first render a deterministic explanation assembled from the measured results and selection rule. This is a functional baseline and should be described accurately in the demo.

### AI integration

Use an ElevenLabs agent with its configured language model and a read-only get_experiment_summary tool. Verify that the provided account includes agent/model access; a speech-only entitlement does not establish that. A separately available text model can use the same summary endpoint. [ElevenLabs webhook tools](https://elevenlabs.io/docs/eleven-agents/customization/tools/webhook-tools)

The agent should:

1. Fetch the current experiment summary before answering result-specific questions.
2. Describe the actual geometry, loading, units, and evidence status.
3. Compare observed metrics and user-provided costs.
4. Explain the deterministic shortlist.
5. Identify missing information and propose one supported next test.

Suggested demo question: "Which option should I physically test next, and what assumptions could change that choice?"

Numeric values and ranking must come from the structured record. Clearly distinguish a synthetic material scenario from a tested physical material. Keep the report usable when voice or the language model is unavailable. Retain transcripts or visible text so audio is optional.

## 12. Physical validation plan

Physical validation strengthens the project if it fits after P0. It is a conditional milestone because the available released scene may not match a specimen the team can obtain during the event.

### Requirements for a meaningful comparison

- The simulated and physical objects have matching relevant geometry and scale.
- Material assumptions, loading direction, supports, contact conditions, and timing are recorded.
- Use known masses or a measured force; an unweighed object does not establish a force in N.
- Measure deformation with a ruler, scale reference, or another documented method.
- Use one loading condition to calibrate and a different condition for evaluation.
- Keep evaluation observations out of the fitting step.

### Procedure

1. Person A obtains a suitable specimen and records its dimensions, available measuring tools, and video with a scale reference.
2. Person B checks whether the chosen simulation can represent the same setup consistently.
3. Fit only the minimum required parameter set against the calibration observation, documenting fixed assumptions.
4. Freeze the fitted parameters.
5. Predict a second loading condition before comparing with its measurement.
6. Record predicted deformation, observed deformation, absolute error, and measurement uncertainty.
7. Label the result as a comparison under those conditions; report the small sample size.

A sponge filmed separately from an unrelated pillow simulation is a physical illustration, not validation of that simulation. If a matching setup is unavailable, retain simulation_only status and present physical validation as the next experiment.

## 13. Checks appropriate to the build

### Person B: Numerical and backend checks

- [ ] Two identical cached requests resolve to the same experiment inputs and artifacts.
- [ ] Candidate configs differ only in the declared experimental variable.
- [ ] Position arrays and time series contain no NaN/Inf values; unloaded reference length is positive.
- [ ] Export precision is sufficient relative to the reported deformation.
- [ ] At least one representative case remains reasonably consistent with a smaller timestep; document changes if it does not.
- [ ] A zero-load or unchanged-state control behaves plausibly for the chosen supports and gravity setting.
- [ ] Shortlist logic handles no qualifying candidates, tied costs, missing costs, and failed candidates.
- [ ] Unsupported IDs and out-of-range loads are rejected before GPU work starts.
- [ ] Failed runs return useful errors and cannot appear as successful measurements.

### Person A: Application checks

- [ ] A real submitted experiment reaches a terminal state in the deployed browser app.
- [ ] All videos load; play/pause/replay and comparison timing are usable.
- [ ] Assumptions, unit system, engine, cached state, and evidence status remain visible.
- [ ] Illustrative fixtures are excluded from the production demo path.
- [ ] Refreshing or opening a saved experiment restores its results.
- [ ] The interface remains usable without microphone access or audio.
- [ ] Empty, loading, partial, and error states contain no invented measurements.

### Joint claim review

- [ ] Every number in the pitch is either measured or explicitly identified as an assumption.
- [ ] The demonstrated experiment matches the narration and interface labels.
- [ ] Any physical comparison uses matched conditions and a held-out observation.
- [ ] Upstream libraries, assets, and Xplore's own contribution are attributed accurately.

## 14. Risks, decision gates, and fallbacks

| Trigger | Decision | Owner |
| --- | --- | --- |
| No remote GPU can be launched | Resolve account access briefly, then activate analytical baseline if the first gate is missed | B |
| Dependencies prevent a baseline by Gate 1 | Stop broad environment debugging; reduce to a supported reproduction or analytical baseline | B |
| Pillow asset has no practical compression setup | Use the best supported deflection protocol and update the entire story consistently | Joint |
| Runs are too slow for a live demo | Use genuine, labelled cached runs for the main comparison; show live submission separately if feasible | B supplies; A presents |
| A candidate becomes unstable | Reduce the shared timestep or supported parameter range, rerun, and expose only stable scenarios | B |
| No matched physical specimen exists | Retain simulation_only status and show the documented next validation experiment | Joint |
| Agent or voice integration is slow | Use the deterministic result explanation and finish P0 | A |
| The clock reaches 16:30 with missing P0 work | Freeze optional features; complete the existing end-to-end journey | Joint |

### Analytical fallback

Keep the Xplore experiment and comparison interface. For a known, idealized rectangular specimen in small-strain uniaxial compression, an analytical baseline can calculate displacement from force, height, area, and elastic modulus. Document its assumptions and its own input units. Show a simple visualization with measured/computed quantities and identify the engine as analytical_baseline.

This fallback supports a narrower virtual experiment. Update branding copy, the technical explanation, and the submission to reflect the actual engine. A successful analytical example does not establish that PowerSim was integrated.

## 15. Repository layout and collaboration

Proposed layout; these implementation files do not exist yet:

~~~text
Xplore/
  plan.md
  README.md
  frontend/                 # Person A
  backend/                  # Person B
    api.py
    modal_app.py
    runner.py
    metrics.py
    ranking.py
  shared/                   # Joint contract; B owns wire format
    experiment.schema.json
    catalog.fixture.json
    experiment.fixture.json
  configs/                  # Person B: approved test definitions
  docs/                     # A: story/demo; B: validation and provenance
    demo-script.md
    validation.md
    sources.md
  tests/                    # Focused backend numeric/contract checks
~~~

Use branches such as codex/xplore-frontend and codex/xplore-simulation if using Git branches. Keep data, checkpoints, secrets, and large generated artifacts out of ordinary source commits. Record where a reviewer can retrieve the genuine demo artifacts.

Person A changes frontend and presentation files. Person B changes backend, simulation configs, and measurement code. Review shared schema changes together and communicate a breaking change before merging it. Integrate at the scheduled milestones instead of waiting until the final hour.

## 16. Demo and submission

### Two-minute video outline

| Time | Content | Lead |
| --- | --- | --- |
| 0:00-0:15 | The user problem and Xplore's decision-support goal | A |
| 0:15-0:35 | Prepared object, three scenarios, common load, and user constraint | A |
| 0:35-1:00 | Real result videos and numerical comparison | B |
| 1:00-1:20 | Shortlist, cost assumptions, and assistant explanation | A |
| 1:20-1:40 | Physical comparison if available; otherwise repeatability and measured runtime | B |
| 1:40-2:00 | Evidence achieved, potential impact, and next validation step | A |

### A concise story to rehearse

"A small product team needs to choose which cushioning option to prototype. Xplore runs the same virtual experiment across three material scenarios, compares their deformation, and explains which options meet the designer's target. We can reproduce each result from its saved inputs. Our next step is validating those comparisons against matching physical tests."

Replace the last sentence with the actual held-out comparison and measured error if that milestone is achieved. Use the actual demonstrated object and loading protocol in every version of the pitch.

### Submission package

- [ ] Xplore title and one-sentence description.
- [ ] The target user and specific decision supported.
- [ ] Deployed app and repository links.
- [ ] Both team members added to the submission and repository.
- [ ] A video within the two-minute limit and its required link.
- [ ] A clear description of what A and B implemented.
- [ ] The actual simulation engine, source attribution, and asset provenance.
- [ ] Measurements, assumptions, limitations, and achieved evidence status.
- [ ] Selected overall/sub-challenge tracks consistent with what was built.
- [ ] One genuine saved example accessible to reviewers.

## 17. First fifteen minutes

**Person A:** Confirm registration, scaffold the app, and create setup/results screens from the shared fixture.

**Person B:** Verify a Modal GPU, inspect the released scene assets, and start the smallest credible reproduction.

**Together:** Agree the contract and the first feasibility checkpoint. At that checkpoint, choose the real supported object, loading protocol, and metric. From then on, optimize for one complete and reproducible experiment journey.

## 18. Primary references

Technical capabilities were checked against these sources on 7 November 2026. The project-specific interfaces, role split, thresholds, and schedule above are proposed implementation decisions. No simulations, deployment, or physical validation have been executed as part of preparing this plan.

- [PowerSim repository and examples](https://github.com/nttung1110/PowerSim)
- [PowerSim paper](https://arxiv.org/html/2609.38153v1)
- [Scene download script](https://github.com/nttung1110/PowerSim/blob/main/scripts/download_checkpoints.py)
- [PowerSim simulation implementation](https://github.com/nttung1110/PowerSim/blob/main/powersim/foam_evolve/simulate.py)
- [PowerSim environment dependencies](https://github.com/nttung1110/PowerSim/blob/main/requirements.txt)
- [Modal GPU availability](https://modal.com/docs/guide/gpu)
- [CUDA on Modal](https://modal.com/docs/guide/cuda)
- [Modal asynchronous jobs](https://modal.com/docs/guide/job-queue)
- [Modal persistent storage](https://modal.com/docs/guide/volumes)
- [ElevenLabs agent webhook tools](https://elevenlabs.io/docs/eleven-agents/customization/tools/webhook-tools)
- [GreatUniHack event schedule](https://greatunihack.com/)
- [GreatUniHack submission requirements](https://greatunihack-2026.devpost.com/)

# Xplore

Grab and deform a soft object, then compare material scenarios to decide which
physical prototype to test next.
The project scope and role split are in [plan.md](plan.md).

The main frontend includes live mouse interaction with a GPU PowerSim MPM solver,
plus a genuine three-candidate compression-pulse comparison, persistent experiment
records, synchronized videos, measured time series and a deterministic shortlist.
The shared v1.0 experiment schema is unchanged. Live gestures are temporary and
separate from the repeatable recorded comparison.

**These results are exploratory.** Halving the timestep changed Balanced's peak by
11.8% (1.46 percentage points), so the 5% convergence goal was not met. Every
shortlist is provisional and physical validation remains pending.

- API: https://tnberkec--xplore-simulation-api.us-east.modal.run
- Grab and deform: https://tnberkec--xplore-simulation-api.us-east.modal.run/sandbox
- Live interaction and its limits: [docs/interactive-handoff.md](docs/interactive-handoff.md).
- Interactive API docs: https://tnberkec--xplore-simulation-api.us-east.modal.run/docs
- Genuine saved example: https://tnberkec--xplore-simulation-api.us-east.modal.run/v1/examples/example.json
- Person A integration: [docs/api-handoff.md](docs/api-handoff.md).
- Experiment and evidence: [docs/validation.md](docs/validation.md).

| Scenario | Stiffness multiplier | Peak normalized compression |
| --- | --- | --- |
| Flexible | 0.5 | 15.54% |
| Balanced | 1.0 | 12.41% |
| Firm | 2.0 | 9.70% |

Only the tested reference load multiplier 1.0 is enabled. These are hypothetical
parameter scenarios, not sourced or validated commercial materials.

## Local backend checks

```sh
python3.11 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python -m unittest discover -s tests -v
backend/.venv/bin/python shared/validate.py
```

## PowerSim reproduction

We started with the pillow drop because PowerSim ships a runnable example for the
chosen pillow asset. Reproducing its original settings verifies the GPU environment,
checkpoint loading, solver, state export, and video rendering before introducing
custom loading or measurement changes. It remains an independent feasibility
baseline; the comparison now uses one isolated pillow and a short controlled pulse.

Fetch the recorded upstream revision (the cache and large outputs are ignored):

```sh
git clone https://github.com/nttung1110/PowerSim.git .cache/PowerSim
git -C .cache/PowerSim checkout 24266e5264a213bceb426796ce91e12a555e2f69
modal run backend/modal_probe.py
modal run backend/modal_app.py --stage prepare
modal run backend/modal_app.py --stage baseline
modal run backend/modal_app.py --stage geometry
modal run backend/modal_app.py --stage benchmark --force 0.02 --dt 0.001
modal deploy backend/modal_app.py
```

Modal authentication must already be configured. The prepare stage downloads only
the released pillow scene to the `xplore-experiments` Volume. The baseline stage
reproduces the released pillow drop and downloads the clip and two stills to
`outputs/baseline/`. A baseline output directory is never silently overwritten.
Use `modal run backend/modal_app.py --stage fetch` to recover the completed
baseline's manifest and previews without rerunning the GPU. The local result
manifest is in `docs/baseline-result.json`.

The source export adapter in `backend/state_export.py` adds an actual pre-step
reference, stable particle IDs, float32 solver positions, and timestep metadata
for controlled experiments. It is not applied to the initial upstream reproduction.
The comparison fixes the upper/lower 15% of the isolated pillow by initial height,
supports the lower group, and loads the upper group for 0.1 simulation seconds.
See [validation](docs/validation.md) for the full protocol and numerical limitations.

The benchmark stages reuse versioned genuine caches. Normal browser requests at the
supported settings reuse those caches and preserve the original execution timings.
Changing only the target or costs creates a new record without rerunning physics.
The default zero-load and refinement checks remain part of the benchmark record.

To check the deployed flow and download the clips:

```sh
backend/.venv/bin/python scripts/verify_deployment.py https://tnberkec--xplore-simulation-api.us-east.modal.run
```

PowerSim and its vendored dependencies retain their upstream licenses and notices.
PowerSim: Trong-Tung Nguyen and Anand Bhattad,
https://github.com/nttung1110/PowerSim (Apache-2.0). Asset provenance is recorded by
the prepare stage; assets are sourced from https://huggingface.co/datasets/Tung11/PowerSim.
See [source and license notes](docs/sources.md).

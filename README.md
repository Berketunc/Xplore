# Xplore

Virtual material comparisons for deciding which physical prototype to test next.
The project scope and role split are in [plan.md](plan.md).

Person B's feasibility work has verified Modal GPU access and reproduced the
released PowerSim pillow drop: 150 finite-state frames, a three-second H.264 clip,
and 190.91 seconds of first-run simulation/rendering time. The comparison protocol,
measurement regions, and API deployment remain to be established. See
[docs/feasibility.md](docs/feasibility.md) for measured evidence and execution controls.

## Local backend checks

```sh
python3.11 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python -m unittest discover -s tests -v
```

## PowerSim reproduction

We started with the pillow drop because PowerSim ships a runnable example for the
chosen pillow asset. Reproducing its original settings verifies the GPU environment,
checkpoint loading, solver, state export, and video rendering before introducing
custom loading or measurement changes. This is the feasibility baseline described
in the plan; a controlled cushioning compression experiment remains a separate step.

Fetch the recorded upstream revision (the cache and large outputs are ignored):

```sh
git clone https://github.com/nttung1110/PowerSim.git .cache/PowerSim
git -C .cache/PowerSim checkout 24266e5264a213bceb426796ce91e12a555e2f69
modal run backend/modal_probe.py
modal run backend/modal_app.py --stage prepare
modal run backend/modal_app.py --stage baseline
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
for subsequent controlled experiments. It is not applied to the initial upstream
reproduction. Quantitative experiment regions and controls remain to be frozen.

PowerSim and its vendored dependencies retain their upstream licenses and notices.
PowerSim: Trong-Tung Nguyen and Anand Bhattad,
https://github.com/nttung1110/PowerSim (Apache-2.0). Asset provenance is recorded by
the prepare stage; assets are sourced from https://huggingface.co/datasets/Tung11/PowerSim.

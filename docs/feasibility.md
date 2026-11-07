# Person B feasibility record

This is the historical record of the first upstream reproduction. The current
controlled experiment and deployed API are described in [validation.md](validation.md)
and [api-handoff.md](api-handoff.md).

## Execution controls

- Initial project spending allowance: £5, chosen on 7 November 2026 with the user's authorization.
- Use a conservative USD 5 operational allowance for this feasibility pass; actual Modal billing is in USD.
- One L40S container at a time, no automatic retries, short idle window.
- GPU access probe: 60-second hard timeout. Reproduction: at most 600 seconds per invocation.
- Track each invocation and stop before the remaining allowance cannot cover its worst-case compute reservation.
- This is an application-side allowance, not a configured Modal account billing limit. Account credits and billing spend have not yet been inspected.

## Source

- PowerSim: https://github.com/nttung1110/PowerSim
- Pinned revision: `24266e5264a213bceb426796ce91e12a555e2f69`
- Source is kept in ignored `.cache/PowerSim`; no checkpoints or secrets belong in Git.
- Upstream license: Apache-2.0. Preserve upstream notices and record asset provenance separately.
- Runtime target: Python 3.11; upstream pinned dependencies and CUDA 12.8 wheel index.
- Runtime image built successfully with all upstream pinned direct dependencies.
- Dataset revision: `78e400018cb9fb20a0e5a62a9138805379055efb`.
- Pillow checkpoint download: 1,170,974,629 bytes; camera bundle: 2,425,883 bytes.
- Full asset checksums are in [prepare-result.json](prepare-result.json).

## Initial observations

- Existing Modal profile authenticated successfully through `modal app list`.
- Remote access probe passed: NVIDIA L40S, 46,068 MiB reported memory, driver 610.57.04.
- Probe application: https://modal.com/apps/tnberkec/main/ap-4X5d0hgLEbz75Us3adZw6a
- Nine focused local numeric/shortlist checks pass with Python 3.11 and NumPy 2.1.2.
- `pillow_drop` is a gravity-driven drop onto a sofa, not a released compression test.
- `ficus_poke` is a supported elastic deflection example and a possible fallback.
- The public comparison catalog remains provisional until loading, metric regions, and stable variants are verified.
- The released pillow-drop simulation has now been reproduced. Physical calibration and validation remain pending.
- This establishes a working scene; a controlled compression/deflection comparison and fixed metric regions are not yet established.

## Measurement implementation

- `backend/metrics.py` computes compression or support-relative deflection from fixed groups.
- The metric preserves signed samples and reports the peak positive value over a fixed interval.
- Source state is required to have stable particle order; the export adapter records the corresponding scene particle IDs.
- Regions, loading axis, and reference length must be fixed and persisted before candidate comparisons.
- `backend/state_export.py` and `patches/powersim-state-export.patch` record the additive adapter for the pinned simulation source. The patched source passes a Python syntax check.
- The original released reproduction does not use this adapter. Its float16 post-step exports are only used for a finite-state check, not a reported deformation metric.

## Invocations

| Stage | Modal application | Outcome |
| --- | --- | --- |
| GPU access | `ap-4X5d0hgLEbz75Us3adZw6a` | Passed |
| Environment and selected assets | `ap-o0i66xti9IlaaLJBs50uPU` | Passed; asset stage 12.11 seconds, image build separate |
| Released pillow-drop reproduction | `ap-yNRfdQJRXA1fTcaYs3r9lM` | Simulation passed; local return decoding recovered separately |
| Artifact recovery on CPU | `ap-oRI7YRYn6lIVdO04TcvixW` | Passed; no additional GPU run |

The GPU probe reserves at most 60 seconds and the reproduction at most 600 seconds.
At the recorded resource rates, those GPU allocations plus their configured CPU/RAM
are conservatively below USD 0.42 before initialization, image build, and storage.
This is a resource-rate estimate, not an account billing measurement.

## Reproduction result

- Original released physics settings: `config/pillow_drop.json`, train camera 87, no per-particle material field override.
- All 150 exported position arrays are finite. The source's float16 output is suitable for this finite-state check, not the quantitative metric.
- Runtime of the simulation subprocess, including rendering, initial kernel compilation, state writes, and video encoding: **190.9056 seconds**. Queue time, environment build, checkpoint download, and subsequent finite-state verification are excluded.
- Output: H.264, yuv420p, 448×448, 50 fps, 150 frames, three seconds, 140,376 bytes.
- First and final stills were visually inspected. The scene shows pillows falling into a woven chair with a cushion.
- The recorded manifest is [baseline-result.json](baseline-result.json). Full runtime package versions and the dataset README are saved alongside the downloaded clip in `outputs/baseline/`.
- Local artifact: `outputs/baseline/output.mp4`. Persistent source artifact: Modal Volume `xplore-experiments`, `baseline/pillow-drop/output.mp4`.
- A result-return decoding error arose because `torch.__version__` is a TorchVersion object. The worker now casts it to a plain string. The existing JSON manifest and video were recovered on CPU; the simulation was not rerun.
- There is no browser artifact URL or deployed experiment API yet. The agreed API wire contract has not been changed.

## Next gate

Freeze the actual loading protocol, ROI/support groups (or upper/lower groups), axis,
reference length, and aggregation interval. Then apply the recorded export adapter,
vary only the intended material stiffness assignment, and run the candidate/control
and timestep checks before publishing the catalog. The released drop clip alone
does not demonstrate a controlled compression test or physical material properties.

## Reference rates

Rates inspected on 7 November 2026 at https://modal.com/pricing:

- L40S: USD 0.000542 per second.
- CPU physical core (2 vCPU equivalent): USD 0.0000131 per second.
- RAM: USD 0.00000222 per GiB-second.
- Storage and egress are separate; record actual usage when available.

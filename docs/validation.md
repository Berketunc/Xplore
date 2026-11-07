# Experiment evidence and limitations

## Current result

The backend serves a real **exploratory pillow compression-pulse comparison**.
Physical validation has not been performed. A timestep refinement check did not
meet the chosen 5% goal, so every shortlist is provisional. No manufacturing
accuracy, waste reduction or commercial savings have been measured.

| Candidate | E multiplier | Peak compression | Original timed execution | Sampled peak GPU memory |
| --- | --- | --- | --- | --- |
| Flexible | 0.5 | 15.535634% | 49.9765 s | 6,266 MiB |
| Balanced | 1.0 | 12.412118% | 98.9120 s | 5,652 MiB |
| Firm | 2.0 | 9.702342% | 115.1854 s | 5,008 MiB |

Execution time includes the simulation subprocess, rendering, state processing
and media packaging. Queue delay, container initialization and asset download
are excluded. Cache hits preserve these original timings; they do not imply a
new GPU execution. Memory is sampled once per second with `nvidia-smi`; it is
an observed sampled maximum, not a guaranteed exact peak.

## Reproducible protocol

- Upstream PowerSim commit: `24266e5264a213bceb426796ce91e12a555e2f69`.
- Dataset: `Tung11/PowerSim`, revision `78e400018cb9fb20a0e5a62a9138805379055efb`.
- Checkpoint: `pillow2sofa_gs_fewer_points`; exact asset hashes in `prepare-result.json`.
- Selection: largest connected component of the released scene's particles at
  normalized z in (1.08, 1.33), connected by distance 0.012. It contains 25,104
  particles belonging to one pillow. The chair and other pillows are hidden and
  not simulated. The preparation code is in `backend/modal_app.py` and `backend/controlled.py`.
- The selected object's largest bounding-box side is normalized to 1.0 for MPM.
  Physical length, force and material units of the released capture are not calibrated.
- Fixed upper/lower groups: upper/lower 15% of initial MPM z coordinates. Membership
  and original scene particle IDs are saved before stepping and checked on export.
- Lower region: zero-velocity grid and particle constraints. Upper region: uniform
  downward force per particle, magnitude 0.02 in simulator units, active for 0.1
  simulation seconds. Gravity is disabled. There is no simulated rigid loading plate.
- Elastic fixed-corotated material (`jelly` in the released solver), baseline E
  10,000, Poisson's ratio 0.3, density 2,000 in simulator conventions. Candidate
  E values are 5,000 / 10,000 / 20,000. Other settings are identical.
- Grid: 100³ over a domain of side 2.0. Common substep: 0.001. Frame interval: 0.02.
  Duration: 2.0 simulation seconds. Grid velocity damping is scaled with timestep
  to preserve its decay rate over simulation time.
- Seed: 0. Released train camera 87, with a fixed crop applied identically to all
  output frames. The initial image is included at video t=0; 101 H.264/yuv420p
  frames at 50 fps produce a 2.02-second file with a one-frame final hold.

## Primary metric

For fixed upper and lower groups, let d(t) be the separation of their centroids
along +z and let d₀ be their actual pre-step separation. The signed series is
`100 × (d₀ − d(t)) / d₀`; the reported metric is its peak positive value over
0–2.0 seconds. It measures geometric axial compression under this protocol,
including any bending contribution to the fixed-axis centroid separation.

The reference separation is approximately 0.59172153 MPM units. The export saves
float32 solver positions, stable particle IDs, coordinate transforms and timestep
metadata. Metrics are computed in float64. The original upstream float16 post-step
exports are not used to calculate this metric. Full groups/config/metadata are
available through each run's approved artifact links.

## Checks and unresolved uncertainty

- All reference and sampled position arrays are finite; reference separation is positive.
- Candidate configs differ only in E. No spatial material field overrides it.
- The zero-load control measured **0.0%** peak compression.
- Support centroid drift is below 0.1% of the reference separation for every candidate.
- Sampled Courant estimates, combining measured particle speed and the initial
  elastic wave-speed estimate, are 0.1181 / 0.1546 / 0.2066 for Flexible / Balanced /
  Firm, below the configured 0.4 bound. This is a numerical diagnostic, not a proof
  of convergence or physical validity.
- Halving Balanced's timestep from 0.001 to 0.0005 changes the peak from
  **12.412118% to 10.949823%**: **1.462295 percentage points**, or **11.7812% relative**.
  This fails the 5% convergence goal. `numerical_quality.status` is
  `timestep_sensitive`; `validated` is false in the registry.
- The catalog can expose a runnable exploratory test while numerical validation
  remains incomplete. The warning is in the scene description, assumptions,
  result record, shortlist notes and assistant summary. Every shortlist is provisional.
- Near-threshold classifications may change with numerical settings. These values
  are not evidence of real commercial material performance. Spatial refinement,
  improved specimen/support modeling and matched physical tests remain future work.

Earlier sustained-load trials showed 15–19% timestep sensitivity across several
step sizes and were not adopted as the final protocol. The short pulse provides
a bounded transient experiment, but it does not eliminate the sensitivity. We
preserve that failed numerical check rather than labelling the result converged.

## Artifacts and checks

`benchmark-result.json` contains the genuine run records, cache identities, control
identities, numerical-quality record and saved example ID. Source state and media
remain on Modal Volume `xplore-experiments`; checkpoints and large outputs are
excluded from Git. Use the API artifact links or the documented Modal commands.

Eighteen local checks cover numeric metrics, ranking edge cases, schema responses,
request validation, saved-record recovery, partial failures, byte ranges and warning
preservation. All three final MP4s decode successfully; initial/final stills were
visually inspected. Deployed HTTP verification is recorded separately in
`deployment-result.json` and all recorded HTTP checks passed.

The deployed submit-to-completed check measured **1.41 seconds** for a complete
genuine cache hit, after adding the direct-cache path. This is an HTTP client
measurement, excluding browser rendering; the original GPU runtimes above remain
attached to the reused results.

Person A's frontend passed TypeScript checking and its Vite production build with
the live API configuration. Automated visual/browser playback verification was
not completed because the browser connection was unavailable; the optional native
Chrome check was skipped. Actual browser playback and presentation should be
checked by Person A. HTTP byte ranges and full MP4 decoding were verified.

The independent released pillow-drop reproduction is recorded in
`baseline-result.json` and `feasibility.md`. It established a working upstream
pipeline; it is not the compression experiment or a physical validation result.

## Costs

`spend-snapshot.json` records Modal's reported Xplore costs as of its timestamp.
It includes development trials and may lag current/in-flight use. It is not a
final invoice. The initial allowance remains £5, with a conservative USD 5
operational allowance and serial, bounded GPU invocations.

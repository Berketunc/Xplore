# Sources, contribution and licensing

- **PowerSim**, Trong-Tung Nguyen and Anand Bhattad:
  https://github.com/nttung1110/PowerSim, pinned commit
  `24266e5264a213bceb426796ce91e12a555e2f69`.
- Paper: https://arxiv.org/html/2609.38153v1. Its discussion explains that the
  representation/physics coupling is approximate and recovered parameters depend
  on density, scale and boundary assumptions.
- Released assets: https://huggingface.co/datasets/Tung11/PowerSim, pinned dataset
  revision `78e400018cb9fb20a0e5a62a9138805379055efb`. The dataset README identifies
  this checkpoint as PhysGaussian's pillow2sofa scene distilled to PowerFoam.
- The rendering and MPM implementations are PowerSim's bundled PowerFoam and
  PhysGaussian sources. Their upstream notices remain in the pinned source tree.
- The PowerSim and bundled PowerFoam code carry Apache-2.0 licenses; copies are
  retained in `docs/licenses/`. The dataset card does not declare a separate asset
  license. We record asset provenance separately and do not commit checkpoints.
- Modal runtime/storage/API references:
  https://modal.com/docs/guide/gpu,
  https://modal.com/docs/guide/volumes,
  https://modal.com/docs/guide/job-queue,
  https://modal.com/docs/guide/webhooks.
- Interactive browser graphics: Three.js 0.180.0, loaded from the pinned jsDelivr
  ES module. Three.js authors, MIT license:
  https://github.com/mrdoob/three.js/blob/r180/LICENSE.

Xplore's contribution is the controlled experiment workflow: single-pillow
selection, bounded loading, precise reference/state exports, deformation metrics,
deterministic shortlist, versioned cache, persistent job/record handling, HTTP
artifacts, bounded mouse-to-solver interaction and the frontend integration.
Xplore does not claim authorship of the
underlying MPM method, PowerSim, PowerFoam, PhysGaussian or the released asset.

The recorded source adapter is additive and is in `backend/state_export.py` and
`patches/powersim-state-export.patch`. It saves a genuine pre-step reference,
stable IDs, float32 positions, timing metadata and sampled velocity diagnostics.

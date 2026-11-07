# Xplore — Two-minute presentation

Four slides, including a live demo in place of slide 2. Person A opens and closes;
Person B handles the demo and technical results. Rehearse to the timings below,
including the pauses for mouse interaction.

## Positioning

**Xplore is an interactive material-exploration prototype for materials science
and engineering. Soft robot gripper pads are the focused use case demonstrated
in this build.**

Present the broader application as the direction of the project. The implemented
scope is a limited set of procedural soft elastic specimens with geometry and
stiffness controls. A gripper pad and a material test block share that workflow.
Broader material classes, calibrated commercial properties and predictive
engineering accuracy have not been demonstrated. Describe the prototype as a
starting point for material exploration rather than a general-purpose materials
science platform. This positioning note is preparation guidance, not spoken text.

| Time | Slide | Speaker |
| --- | --- | --- |
| 0:00–0:25 | Xplore: Make Material Behaviour Tangible | Person A |
| 0:25–1:00 | One Use Case: A Robot Gripper Pad — live app | Person B |
| 1:00–1:30 | Built for Interaction. Backed by Simulation. | Person B |
| 1:30–2:00 | A Starting Point for Material Exploration | Person A |

## Before presenting

- Restart and check the local frontend and Modal backend 20–30 minutes beforehand.
  They were stopped at the user's request; this document does not restart them.
- Open `http://127.0.0.1:5173/`. Use **+ New experiment** to prepare the default
  robot gripper pad: width 1.0, depth 0.6, thickness 0.25, Balanced stiffness 1×.
- Capture a short recording of the working pad as a backup before presenting.
- Start a fresh live physics session shortly before the talk. Allow for GPU startup,
  then begin the pitch promptly once the pad is ready. Sessions allow 90 live
  seconds after readiness; finish the interaction by 1:00 in the pitch.
- Use that prepared session for the demo. Creating another experiment or changing
  material settings requires a new session, so show those controls without editing
  them during the two-minute pitch. Reset restores the specimen but does not extend
  the session timer.
- Keep the browser ready to switch to after slide 1, and the results slide ready
  to return to after the demo.

## Slide 1 — Xplore: Make Material Behaviour Tangible

**Time:** 0:00–0:25  
**Speaker:** Person A

**On screen:** Project name, “Interactive exploration for materials science,” and
“Configure → Interact → Explore.” Use the gripper pad and material block as images
of the actual supported specimens. Label robotics as the first focused use case.

**Full script:**

> Understanding how a material deforms matters across research, education and
> engineering. We want to make that exploration more accessible.
>
> Xplore lets you configure a virtual specimen, adjust its stiffness, and deform
> it with your mouse. For this prototype, we focused on one concrete use case:
> a silicone-inspired robot gripper pad.

**Transition:** Switch to the prepared live app and hand over to Person B.

## Slide 2 — One Use Case: A Robot Gripper Pad

**Time:** 0:25–1:00  
**Speaker:** Person B  
**On screen:** The live app, with the default pad already running.

**Full script and actions:**

> For our robotics use case, this is a silicone-inspired pad mounted on a fixed
> base. We configured its dimensions and stiffness.
>
> I’ll grab the surface and press it.

*Grab the upper surface and drag slowly to press it. Pause for three seconds.*

> You can see the local deformation. Now I release it and watch the response.

*Release the pointer and pause briefly.*

> Reset restores the initial state.

*Click Reset.*

> The GPU physics solver calculates this response as I interact.

**Transition:** Return to slide 3.

## Slide 3 — Built for Interaction. Backed by Simulation.

**Time:** 1:00–1:30  
**Speaker:** Person B

**On screen:**

- **11,275 simulated particles in the gripper pad**
- **About 31 received updates per second in the pad test**
- **Configurable geometry and stiffness**

*Small caption: Update rate measured through the deployed WebSocket; browser
rendering performance was not measured.*

**Full script:**

> Our gripper-pad example contains over eleven thousand simulated particles.
> In our deployed test, we received about thirty-one updates per second.
>
> We use the PhysGaussian solver bundled with PowerSim, running on Modal. We built
> the specimen configuration, browser interaction and streaming workflow.
>
> We also tested a separate material block with custom dimensions and stiffness.

**Transition:** Hand back to Person A.

## Slide 4 — A Starting Point for Material Exploration

**Time:** 1:30–2:00  
**Speaker:** Person A

**On screen:** “Today: soft elastic specimens” and
“Next: controlled comparisons → calibration → physical validation.”

**Full script:**

> Our broader vision is an interactive workspace for exploring material behaviour.
> Today, we support a limited set of soft elastic specimens, and our model is not
> yet calibrated or physically validated.
>
> Next, we will compare stiffness under identical loading and test a matching
> physical sample.
>
> Xplore makes material behaviour tangible, starting with soft robotics.

## If the live demo cannot run

Switch to the backup recording captured beforehand and use this introduction:

> The live connection isn’t ready, so I’ll show a recording of the same gripper-pad
> interaction.

Continue the demonstration narration while the recording plays. If no recording
is available, show the configured specimen and move to the measured-results slide.

## Evidence behind the pitch

- The default pad has **11,275 physics particles** and **802 display vertices**.
- Its recorded native WebSocket test received **30.86 updates/s** and verified
  non-rigid deformation, finite positions, release, reset and stop.
- Additional checks passed for a pad at stiffness 2× and thickness 0.16, and a
  0.8 × 0.5 × 0.4 block at custom stiffness 1.3×. These are different configurations,
  not a controlled comparison of material performance.
- Dimensions and displacement use relative simulator units. Grip force,
  commercial silicone properties, physical accuracy, prototype savings and
  numerical convergence have not been validated.
- The historical pillow compression percentages are not gripper-pad results.
- The gripper-pad performance numbers do not establish performance across material
  classes. The current soft elastic model does not establish support for general
  materials discovery, plasticity, fracture, thermal behaviour or chemical properties.
- The frontend runs locally and uses Modal for remote GPU physics. Live tests
  are temporary; AI/voice and mouse-session saving are excluded from this build.

Sources: [validation and limitations](validation.md),
[live workspace protocol](interactive-handoff.md),
[default pad verification](robotics-verification-gripper_pad-balanced.json),
[firm pad verification](robotics-verification-gripper_pad-firm.json),
[custom block verification](robotics-verification-material_block-balanced.json),
and [source attribution](sources.md).

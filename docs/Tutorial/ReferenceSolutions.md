# Reference Solutions

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

Read the problem and its acceptance checks before opening a hint or answer.
Each link below lands on that protected attempt: three progressive hints and
the worked stage solution are ready there. Source links in the chapter lead to
the assembled reference, which includes later additions.

Which chapters to read for a goal: [routes](../VulkanTutorial.md#routes).

## Problems and ready answers

Each row lists a chapter's attempts in reading order. `(pair <stage>)` after
an attempt marks a prepared Starter/Solution pair, with the stage ID to pass
to the runner; [Working a prepared exercise](#working-a-prepared-exercise)
says how to run one. `(CPU pair <id>)` marks a content-addressed CPU source
checkpoint instead, which the
[checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md)
prepares and checks; the table of CPU checkpoints under
[Runnable support and evidence](#runnable-support-and-evidence) lists them
all. A historical snapshot, marked on its chapter, is a finished source tree
from an earlier commit, not a pair.

| Chapter | Problems And Ready Answers |
| --- | --- |
| [01 - Environment and Build Wiring](01-Environment-And-Build.md) | [CH01-workspace](01-Environment-And-Build.md#ch01-workspace) |
| [02 - Instance, Device, and Queues](02-Instance-And-Device.md) | [CH02-queue-family](02-Instance-And-Device.md#ch02-queue-family) |
| [03 - The Swapchain](03-Swapchain.md) | [CH03-extent](03-Swapchain.md#ch03-extent) |
| [04 - Commands and Synchronization](04-Commands-And-Synchronization.md) | [CH04-frame-order](04-Commands-And-Synchronization.md#ch04-frame-order) |
| [05 - The First Frame](05-First-Frame.md) | [CH05-clear-frame](05-First-Frame.md#ch05-clear-frame) |
| [06 - Shaders and Pipelines](06-Shaders-And-Pipelines.md) | [CH06-triangle](06-Shaders-And-Pipelines.md#ch06-triangle) |
| [07 - ImGui Debug Panels](07-ImGui.md) | [CH07-input](07-ImGui.md#ch07-input), [CH07-scale-a-live-interface](07-ImGui.md#ch07-scale-a-live-interface) |
| [08 - Resources, Memory, and Descriptors](08-Resources-And-Descriptors.md) (historical snapshot `historical-08-foundation`; it predates this chapter's current text: compare structure, not listings) | [CH08-two-pass](08-Resources-And-Descriptors.md#ch08-two-pass) |
| [09 - The Demo Harness](09-Demo-Harness.md) | [CH09-demo-switch](09-Demo-Harness.md#ch09-demo-switch) |
| [10 - Cameras and Depth](10-Cameras-And-Depth.md) | [CH10-projection](10-Cameras-And-Depth.md#ch10-projection), [CH10-fly-motion](10-Cameras-And-Depth.md#ch10-fly-motion) |
| [11 - Meshes](11-Meshes.md) | [CH11-plane](11-Meshes.md#ch11-plane), [CH11-normal-transform](11-Meshes.md#ch11-normal-transform) |
| [12 - The Scene Graph](12-Scene-Graph.md) | [CH12-reparent](12-Scene-Graph.md#ch12-reparent), [CH12-live-mirror](12-Scene-Graph.md#ch12-live-mirror) |
| [13 - Adding a Library: TinyUSDZ](13-Adding-TinyUSDZ.md) | [CH13-stage-report](13-Adding-TinyUSDZ.md#ch13-stage-report) |
| [14 - Importing USD Scenes](14-Importing-USD-Scenes.md) | [CH14-stage-conversion](14-Importing-USD-Scenes.md#ch14-stage-conversion), [CH14-primvar-corner](14-Importing-USD-Scenes.md#ch14-primvar-corner) |
| [15 - Materials and Textures](15-Materials-And-Textures.md) | [CH15-texture-input](15-Materials-And-Textures.md#ch15-texture-input), [CH15-light-contribution](15-Materials-And-Textures.md#ch15-light-contribution) |
| [16 - Lights](16-Lights.md) | [CH16-resolve-light](16-Lights.md#ch16-resolve-light) |
| [17 - Shadows](17-Shadows.md) | [CH17-shadow-lookup](17-Shadows.md#ch17-shadow-lookup), [CH17-stable-grid](17-Shadows.md#ch17-stable-grid) |
| [18 - Anti-Aliasing](18-Anti-Aliasing.md) | [CH18-alpha-coverage](18-Anti-Aliasing.md#ch18-alpha-coverage) |
| [19 - Instancing and Indirect Draws](19-Instancing-And-Indirect.md) (historical snapshot `historical-19-renderer`; it predates this chapter's current text: compare structure, not listings) | [CH19-draw-modes](19-Instancing-And-Indirect.md#ch19-draw-modes) |
| [20 - Compute Fundamentals](20-Compute-Fundamentals.md) (historical snapshot `historical-20-compute`; it predates this chapter's current text: compare structure, not listings) | [CH20-life-step](20-Compute-Fundamentals.md#ch20-life-step) |
| [21 - GPU Particles](21-GPU-Particles.md) | [CH21-gpu-counts](21-GPU-Particles.md#ch21-gpu-counts), [CH21-soft-particles](21-GPU-Particles.md#ch21-soft-particles) |
| [22 - Deferred Shading](22-Deferred-Shading.md) | [CH22-position](22-Deferred-Shading.md#ch22-position), [CH22-tile-list](22-Deferred-Shading.md#ch22-tile-list) |
| [23 - The Sky](23-The-Sky.md) | [CH23-sky-direction](23-The-Sky.md#ch23-sky-direction), [CH23-deferred-sky](23-The-Sky.md#ch23-deferred-sky) |
| [24 - Image-Based Lighting](24-Image-Based-Lighting.md) | [CH24-diffuse](24-Image-Based-Lighting.md#ch24-diffuse), [CH24-specular-lut](24-Image-Based-Lighting.md#ch24-specular-lut) |
| [25 - Grass I: Blades](25-Grass-Blades.md) | [CH25-an-empty-field](25-Grass-Blades.md#ch25-an-empty-field), [CH25-decode-the-strip](25-Grass-Blades.md#ch25-decode-the-strip), [CH25-bend-without-moving-the-root](25-Grass-Blades.md#ch25-bend-without-moving-the-root), [CH25-normals-from-the-curve](25-Grass-Blades.md#ch25-normals-from-the-curve) |
| [26 - Grass II: GPU Generation](26-Grass-GPU-Generation.md) | [CH26-generate-a-stable-field](26-Grass-GPU-Generation.md#ch26-generate-a-stable-field), [CH26-reject-only-proven-occlusion](26-Grass-GPU-Generation.md#ch26-reject-only-proven-occlusion) |
| [27 - Grass III: The Look](27-Grass-Look.md) | [CH27-clumps-and-their-bounds](27-Grass-Look.md#ch27-clumps-and-their-bounds), [CH27-a-gust-is-shared-state](27-Grass-Look.md#ch27-a-gust-is-shared-state), [CH27-edge-on-visibility](27-Grass-Look.md#ch27-edge-on-visibility), [CH27-width-without-excess-coverage](27-Grass-Look.md#ch27-width-without-excess-coverage), [CH27-a-rounder-normal](27-Grass-Look.md#ch27-a-rounder-normal), [CH27-distance-shading-without-a-seam](27-Grass-Look.md#ch27-distance-shading-without-a-seam), [CH27-separate-light-terms](27-Grass-Look.md#ch27-separate-light-terms), [CH27-a-shadow-proxy-with-a-budget](27-Grass-Look.md#ch27-a-shadow-proxy-with-a-budget), [CH27-an-interaction-that-composes](27-Grass-Look.md#ch27-an-interaction-that-composes) |
| [28 - Clouds](28-Clouds.md) | [CH28-a-layer-with-a-known-answer](28-Clouds.md#ch28-a-layer-with-a-known-answer), [CH28-shape-from-independently-testable-inputs](28-Clouds.md#ch28-shape-from-independently-testable-inputs), [CH28-light-with-an-explicit-approximation](28-Clouds.md#ch28-light-with-an-explicit-approximation), [CH28-spend-work-while-controlling-history](28-Clouds.md#ch28-spend-work-while-controlling-history) |
| [29 - The FFT Ocean](29-FFT-Ocean.md) | [CH29-an-fft-whose-answer-you-can-derive](29-FFT-Ocean.md#ch29-an-fft-whose-answer-you-can-derive), [CH29-maps-with-mathematical-invariants](29-FFT-Ocean.md#ch29-maps-with-mathematical-invariants), [CH29-a-surface-that-reads-the-maps-honestly](29-FFT-Ocean.md#ch29-a-surface-that-reads-the-maps-honestly) |
| [30 - A Rougher Sea](30-A-Rougher-Sea.md) | [CH30-bands-that-neither-duplicate-nor-lose-waves](30-A-Rougher-Sea.md#ch30-bands-that-neither-duplicate-nor-lose-waves), [CH30-control-a-measured-spectrum-in-measured-units](30-A-Rougher-Sea.md#ch30-control-a-measured-spectrum-in-measured-units), [CH30-foam-history-is-state](30-A-Rougher-Sea.md#ch30-foam-history-is-state), [CH30-count-reflected-light-once](30-A-Rougher-Sea.md#ch30-count-reflected-light-once) |
| [31 - Spray](31-Spray.md) | [CH31-a-prop-remains-a-project-asset](31-Spray.md#ch31-a-prop-remains-a-project-asset), [CH31-ask-the-displaced-surface-then-request-spray](31-Spray.md#ch31-ask-the-displaced-surface-then-request-spray), [CH31-concurrent-stamps-need-an-exact-contract](31-Spray.md#ch31-concurrent-stamps-need-an-exact-contract) |
| [32 - A Boat](32-A-Boat.md) (historical snapshot `historical-32-sea`; it predates this chapter's current text: compare structure, not listings) | [CH32-a-floating-body-with-a-measurable-equilibrium](32-A-Boat.md#ch32-a-floating-body-with-a-measurable-equilibrium), [CH32-motion-without-changing-ownership](32-A-Boat.md#ch32-motion-without-changing-ownership) |
| [33 - Path Tracing](33-Path-Tracing.md) | [CH33-throughput](33-Path-Tracing.md#ch33-throughput), [CH33-ray-query](33-Path-Tracing.md#ch33-ray-query) |
| [34 - Debugging and Profiling](34-Debugging.md) | [CH34-capture](34-Debugging.md#ch34-capture), [CH34-validation](34-Debugging.md#ch34-validation) |
| [35 - Seeing Far](35-Seeing-Far.md) | [CH35-expose-the-depth-error](35-Seeing-Far.md#ch35-expose-the-depth-error), [CH35-change-a-convention-as-one-contract](35-Seeing-Far.md#ch35-change-a-convention-as-one-contract) |
| [36 - Terrain to the Horizon](36-Terrain-To-The-Horizon.md) | [CH36-rings-with-a-seam-oracle](36-Terrain-To-The-Horizon.md#ch36-rings-with-a-seam-oracle), [CH36-a-map-with-an-explicit-world-contract](36-Terrain-To-The-Horizon.md#ch36-a-map-with-an-explicit-world-contract), [CH36-a-horizon-without-hiding-near-errors](36-Terrain-To-The-Horizon.md#ch36-a-horizon-without-hiding-near-errors) |
| [37 - Objects at a Distance](37-Objects-At-A-Distance.md) (historical snapshot `historical-37-horizon`; it predates this chapter's current text: compare structure, not listings) | [CH37-objects-retain-their-hierarchy](37-Objects-At-A-Distance.md#ch37-objects-retain-their-hierarchy), [CH37-lod-follows-projected-size](37-Objects-At-A-Distance.md#ch37-lod-follows-projected-size) (pair `ch37-lod`), [CH37-a-forest-is-a-function-of-world-cells](37-Objects-At-A-Distance.md#ch37-a-forest-is-a-function-of-world-cells), [CH37-a-shadow-budget-separate-from-view-reach](37-Objects-At-A-Distance.md#ch37-a-shadow-budget-separate-from-view-reach) |
| [38 - Ground Materials](38-Ground-Materials.md) | [CH38-weights-with-a-conservation-rule](38-Ground-Materials.md#ch38-weights-with-a-conservation-rule), [CH38-close-up-detail-with-correct-data-spaces](38-Ground-Materials.md#ch38-close-up-detail-with-correct-data-spaces), [CH38-cliffs-and-distance-share-a-budget](38-Ground-Materials.md#ch38-cliffs-and-distance-share-a-budget) |
| [39 - Plants](39-Plants.md) and [Renderer convergence](RendererConvergence.md) | [CH39-a-generated-asset-with-a-stable-contract](39-Plants.md#ch39-a-generated-asset-with-a-stable-contract), [CH39-coverage-is-a-measurable-signal](39-Plants.md#ch39-coverage-is-a-measurable-signal), [CH39-bounded-gpu-planting-from-shared-terrain](39-Plants.md#ch39-bounded-gpu-planting-from-shared-terrain), [CH39-make-the-performance-claim-falsifiable](39-Plants.md#ch39-make-the-performance-claim-falsifiable), [CH39-convergence-geometry-owner](RendererConvergence.md#ch39-convergence-geometry-owner), [CH39-convergence-cascade-visibility](RendererConvergence.md#ch39-convergence-cascade-visibility) (pair `renderer-convergence`), [CH39-convergence-fallible-frame](RendererConvergence.md#ch39-convergence-fallible-frame), [CH39-convergence-shared-fft](RendererConvergence.md#ch39-convergence-shared-fft) |
| [40 - Forests to the Horizon](40-Forests-To-The-Horizon.md) | [CH40-bake-a-surface-contract](40-Forests-To-The-Horizon.md#ch40-bake-a-surface-contract), [CH40-stable-handover](40-Forests-To-The-Horizon.md#ch40-stable-handover) (pair `ch40-impostors`), [CH40-measure-the-whole-forest](40-Forests-To-The-Horizon.md#ch40-measure-the-whole-forest) |
| [41 - Grass on the Island](41-Grass-On-The-Island.md) | [CH41-one-coastal-frame](41-Grass-On-The-Island.md#ch41-one-coastal-frame), [CH41-roots-on-the-rendered-surface](41-Grass-On-The-Island.md#ch41-roots-on-the-rendered-surface), [CH41-grass-habitat](41-Grass-On-The-Island.md#ch41-grass-habitat) (pair `ch41-island-grass`) |
| [42 - One Wind](42-One-Wind.md) | [CH42-one-owner](42-One-Wind.md#ch42-one-owner), [CH42-a-turn-is-not-a-jump](42-One-Wind.md#ch42-a-turn-is-not-a-jump) (CPU pair `ch42-integrated-drift`), [CH42-a-lean-that-turns-smoothly](42-One-Wind.md#ch42-a-lean-that-turns-smoothly) |
| [43 - Waves to the Shore](43-Waves-To-The-Shore.md) | [CH43-numerical-bridge](43-Waves-To-The-Shore.md#ch43-numerical-bridge), [CH43-fixed-bed](43-Waves-To-The-Shore.md#ch43-fixed-bed), [CH43-balanced-transport](43-Waves-To-The-Shore.md#ch43-balanced-transport), [CH43-physical-clock](43-Waves-To-The-Shore.md#ch43-physical-clock) (pair `ch43-clock`), [CH43-offshore-contract](43-Waves-To-The-Shore.md#ch43-offshore-contract), [CH43-wet-history](43-Waves-To-The-Shore.md#ch43-wet-history) (pair `ch43-wet-history`), [CH43-opaque-water-inputs](43-Waves-To-The-Shore.md#ch43-opaque-water-inputs) |
| [45 - Scene Documents And Typed Properties](45-Scene-Documents-And-Properties.md) | [CH45-property-bindings](45-Scene-Documents-And-Properties.md#ch45-property-bindings), [CH45-typed-properties](45-Scene-Documents-And-Properties.md#ch45-typed-properties), [CH45-generated-inspector](45-Scene-Documents-And-Properties.md#ch45-generated-inspector), [CH45-document-round-trip](45-Scene-Documents-And-Properties.md#ch45-document-round-trip), [CH45-transactional-load](45-Scene-Documents-And-Properties.md#ch45-transactional-load), [CH45-gpu-activation](45-Scene-Documents-And-Properties.md#ch45-gpu-activation) |
| [46 - Capturing Grass Clumps](46-Capturing-Grass-Clumps.md) | [CH46-capture-a-relightable-clump](46-Capturing-Grass-Clumps.md#ch46-capture-a-relightable-clump) (pair `ch46-grass-capture`), [CH46-horizon-capture-grid](46-Capturing-Grass-Clumps.md#ch46-horizon-capture-grid), [CH46-last-visual-source](46-Capturing-Grass-Clumps.md#ch46-last-visual-source) (pair `ch46-last-visual-source`), [CH46-preserve-covered-area](46-Capturing-Grass-Clumps.md#ch46-preserve-covered-area) |
| [47 - Grass Representation Handover](47-Grass-Representation-Handover.md) | [CH47-stable-clump-identity](47-Grass-Representation-Handover.md#ch47-stable-clump-identity), [CH47-projected-handover](47-Grass-Representation-Handover.md#ch47-projected-handover) (pair `ch47-grass-handover`), [CH47-explicit-sample-coverage](47-Grass-Representation-Handover.md#ch47-explicit-sample-coverage) (pair `ch47-explicit-coverage`), [CH47-live-deformation](47-Grass-Representation-Handover.md#ch47-live-deformation), [CH47-surface-depth](47-Grass-Representation-Handover.md#ch47-surface-depth) |
| [48 - Grass In The Coastal Pipeline](48-Grass-In-The-Coastal-Pipeline.md) | [CH48-persistent-world](48-Grass-In-The-Coastal-Pipeline.md#ch48-persistent-world) (pair `ch48-persistent-world`), [CH48-grass-appearance](48-Grass-In-The-Coastal-Pipeline.md#ch48-grass-appearance) (pair `ch48-grass-appearance`), [CH48-population-reach](48-Grass-In-The-Coastal-Pipeline.md#ch48-population-reach), [CH48-rendered-standalone-surface](48-Grass-In-The-Coastal-Pipeline.md#ch48-rendered-standalone-surface), [CH48-terrain-budget](48-Grass-In-The-Coastal-Pipeline.md#ch48-terrain-budget) (pair `ch48-grass-terrain`), [CH48-coarse-work](48-Grass-In-The-Coastal-Pipeline.md#ch48-coarse-work) (pair `ch48-coarse-work`), [CH48-canonical-source](48-Grass-In-The-Coastal-Pipeline.md#ch48-canonical-source) (pair `ch48-canonical-source`), [CH48-terrain-frame](48-Grass-In-The-Coastal-Pipeline.md#ch48-terrain-frame) (pair `ch48-terrain-frame`), [CH48-shared-frame](48-Grass-In-The-Coastal-Pipeline.md#ch48-shared-frame), [CH48-caster-ownership](48-Grass-In-The-Coastal-Pipeline.md#ch48-caster-ownership) (pair `ch48-caster-ownership`), [CH48-capture-facing](48-Grass-In-The-Coastal-Pipeline.md#ch48-capture-facing) (pair `ch48-capture-facing`), [CH48-filtered-blade-lighting](48-Grass-In-The-Coastal-Pipeline.md#ch48-filtered-blade-lighting), [CH48-measured-budget](48-Grass-In-The-Coastal-Pipeline.md#ch48-measured-budget) |

The optional renderer-refinement branch is entered after Chapter 24. Its
lessons are independent, and separate worked math, actual GPU execution,
appearance and timing evidence. Source-pair verification status is recorded
in the stage guide and roadmap.

| Renderer lesson | Protected problems |
| --- | --- |
| [49 — Bloom And Color Grading](49-Bloom-And-Color-Grading.md) | [CH49-color-order](49-Bloom-And-Color-Grading.md#ch49-color-order), [CH49-bloom-pyramid](49-Bloom-And-Color-Grading.md#ch49-bloom-pyramid) (pair `ch49-bloom-normalization`), [CH49-final-output](49-Bloom-And-Color-Grading.md#ch49-final-output) |
| [50 — Screen-Space Ambient Occlusion](50-Screen-Space-Ambient-Occlusion.md) | [CH50-depth-position](50-Screen-Space-Ambient-Occlusion.md#ch50-depth-position), [CH50-occlusion-field](50-Screen-Space-Ambient-Occlusion.md#ch50-occlusion-field) (pair `ch50-ao-strength`), [CH50-ambient-only](50-Screen-Space-Ambient-Occlusion.md#ch50-ambient-only) |
| [51 — Atmosphere And Aerial Perspective](51-Atmosphere-And-Aerial-Perspective.md) | [CH51-transmittance](51-Atmosphere-And-Aerial-Perspective.md#ch51-transmittance), [CH51-atmosphere-lut](51-Atmosphere-And-Aerial-Perspective.md#ch51-atmosphere-lut), [CH51-finite-segment](51-Atmosphere-And-Aerial-Perspective.md#ch51-finite-segment) (pair `ch51-segment-transmission`) |

Local wind is a separate continuation after Chapter 21, independent of the
renderer-refinement route:

| Particle continuation | Protected problems |
| --- | --- |
| [52 — Wind Fields And Vorticles](52-Wind-Fields-And-Vorticles.md) | [CH52-source-owner](52-Wind-Fields-And-Vorticles.md#ch52-source-owner), [CH52-finite-field](52-Wind-Fields-And-Vorticles.md#ch52-finite-field), [CH52-wind-response](52-Wind-Fields-And-Vorticles.md#ch52-wind-response) |

## Working a prepared exercise

Through Chapter 39 you type every chapter into your own tree. Some problems
also come prepared, in one of three forms:

- A **paired exercise**, marked `(pair <stage>)` above: a Starter and a
  Solution prepared from the same pinned commit of the assembled reference.
  The Starter is the complete reference with one deliberate, buildable
  omission, which is the problem; both run the same acceptance checks.
- A **historical snapshot**, marked on the rows of 8, 19, 20, 32 and 37: the
  source as it stood at a recorded commit, with any declared compatibility
  repairs, as a Solution only. It predates its chapter's current text, so
  compare its structure, not its listings, and it has no acceptance suite to
  check against.
- A **CPU checkpoint**, in the table under
  [Runnable support and evidence](#runnable-support-and-evidence): current
  reference source exported into a small project that builds on its own, with
  a protected oracle. It opens no window, so it certifies no rendering.

**Running a stage.** Open PowerShell 7 at the root of your `reference-main`
checkout, the outer one, not a prepared tree inside it. Each stage line in a
chapter is built from one of these two, with that chapter's stage ID filled
in and any action, configuration or guard flags the chapter adds (the table
below says what each does):

```powershell
.\Tests\TutorialHarness\Stages\Invoke-LearningStage.ps1 -Stage ch37-lod -Variant Starter -ExpectIncomplete
.\Tests\TutorialHarness\Stages\Invoke-LearningStage.ps1 -Stage ch37-lod -Variant Solution
```

The first prepares the Starter under
`Build/LearningStages/ch37-lod/Starter/Source/`, builds it, runs its
acceptance checks and a short scene run, and expects the declared check to
fail. The second does the same for the complete Solution, in its own tree
beside it, where every check must pass. Edit the Starter's `Source` tree, keep
running the commands from the outer checkout, and once your fix is in, run
the Starter again without `-ExpectIncomplete`.

| Parameter | Values (default) | What it does |
| --- | --- | --- |
| `-Stage` | a stage ID | The pair or snapshot to work on |
| `-Variant` | `Starter` (default), `Solution` | Which of the two trees |
| `-Action` | `All` (default), `Prepare`, `Build`, `Check`, `Smoke`, `Verify`, `Repair` | `All` prepares a fresh tree, then builds, checks and runs it, and refuses a tree that already exists. `Prepare` alone never overwrites a tree. `Build`, `Check` and `Smoke` reuse the prepared tree, one phase each. `Verify` builds, checks and runs an already prepared tree in one call. `Repair` applies a snapshot's recorded repairs to a tree prepared before they existed |
| `-Configuration` | `Debug` (default), `Release`, `Dist` | The build configuration; a chapter names the one its stage needs |
| `-ExpectIncomplete` | a switch | Starter only: the declared check must fail, and every other check must pass |
| `-ReuseNativeDependencies` | a switch | Reuses the outer checkout's GLFW, ImGui and TinyUSDZ libraries when their build settings match; any difference builds them from scratch |
| `-BuildWorkers` | `1` (default) or `2` | Project and compiler workers. Keep 1 on a machine short of memory |
| `-MinimumAvailableMemoryMiB` | MiB (0: off) | Refuses to start a build, check or scene run with less free memory than this |
| `-MemoryFloorMiB` | MiB (0: off) | Stops the runner's own child process if free memory falls below this during a run |
| `-HeadroomWaitSeconds` | 0-300 (0) | Waits up to this long for free memory to reach the minimum before refusing |
| `-SmokeTimeoutSeconds` | 1-1800 (180) | The scene run's time limit; a run that reaches it has failed |
| `-Gpu` | part of a device name (`RTX`) | The GPU for the checks and the scene run |
| `-EvidenceName` | a name | Keeps a second device's logs and captures beside the first instead of replacing them, as in `-Gpu Radeon -EvidenceName Radeon` |
| `-MSBuild` | a path | MSBuild, when yours is not Visual Studio 2022 Community's |

The memory flags are for a busy machine and are not part of any check: left
out, they are off. The reference's own runs used 3072 MiB as the minimum for a
build, 3500 for a GPU check and 4100 for a scene run or for any check that
runs the program itself, with 3072 as the floor.

**Reading a Starter's result.** A Starter must compile, run its scene, and
fail only the check its stage declares, with a line that begins `FAIL:` and
matches the stage's declared failure. Any other failure, a build error or a
crash is not the problem the Starter sets: fix that first. A stage whose
checks are all healthy cannot be run with `-ExpectIncomplete`.

**CPU checkpoints.** Their runner is
`Tests\TutorialHarness\Checkpoints\Invoke-SourceCheckpoint.ps1`. It takes
`-Checkpoint <id>`, `-Variant Starter` or `Solution` (the default),
`-Configuration Debug` (the default) or `Release`, `-ExpectIncomplete` for a
Starter's check, and `-Action List` (the default), `Prepare`, `Generate`,
`Build`, `Check`, `Export` or `Verify`. Its Generate, Build and Check phases
carry their own guard: each waits up to 60 seconds for 4100 MiB of free
memory, refuses to start while `SandboxGame`, MSBuild, the compiler, a
tutorial test program or another checkpoint phase is running, stops its own
process tree if free memory falls below 3072 MiB, and stops after 900 seconds.

The [stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md) has the
paths, repairs and evidence each run keeps; the
[checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md) has
content identities, exports and the protected oracles.

## Runnable support and evidence

The current reference is not a substitute for building the earlier stages.
Chapters 2–4 defer their runtime checks until Chapter 5 wires up the frame loop.
The optional soft-particle solution in 21 is compiled into Particles; a zero
soft distance preserves the original path. Chapter 40 adds the far forest;
Chapter 41 adds the bounded coastal grass composition; Chapter 43 develops
the gentle long-wave shoreline, with its current verification status stated
in the chapter. [Chapter 45](45-Scene-Documents-And-Properties.md) adds CPU
scene documents and typed properties; procedural-world authoring remains
partial. Chapter 42 gives the demos one world wind; Chapters 44 and 53 remain
separate planned work. The [runnable-stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md)
distinguishes paired exercises from historical source checkpoints and records
the limits of each.

The Git-based source catalogs contain **21 paired exercises and 5 historical
snapshots**. Written worked answers cover more milestones than those exports:

| Chapters | Paired exercises | Historical snapshots | How to use the remaining problems |
| --- | --- | --- | --- |
| 1–36 | 0 | 4: 8, 19, 20, 32 | Build the growing chapter code and use its worked answer and exit checks |
| 37–41 | 4 | 1: 37 | Use the named pair where provided; other milestones have worked answers |
| 42 | 0 | 0 | Written problems over the current reference; `TutorialWorldWindTests` and `TutorialWorldWindTurnTests` check the owner on the CPU. The content-addressed CPU pair `ch42-integrated-drift` below covers the first attempt of section 2; no Git stage |
| 43 | 2 | 0 | Clock and wet-history pairs; other shoreline problems have worked answers |
| 45 | 0 | 0 | The separate content-addressed CPU checkpoints below cover bindings, hierarchy and documents; no historical Git chapter snapshot |
| 46–48 | 12 | 0 | Use each named pair's source pin; other milestones have worked answers |
| 49–51 | 3 | 0 | Bloom/AO pairs on `bbbe966`, atmosphere on `84b3b99`; all six Debug exports, both-GPU checks and twelve smokes verified |
| 52 | 0 | 0 | Three written local-wind problems and current-reference CPU/GPU targets; no sealed Starter/Solution export. Current run status is in the roadmap. |

A paired exercise omits one behavior from a complete reference checkpoint.
A historical snapshot is a solution at its recorded source commit, with any
declared compatibility repairs. Neither category certifies every intermediate
listing. [The stage manifests](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/Stages.psd1)
and [historical catalog](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/HistoricalCheckpoints.psd1)
are authoritative for available exports; fresh run evidence establishes what
was actually checked.

A second catalog provides [durable CPU source checkpoints](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md).
These snapshot selected current-reference sources and dependency headers into
independently buildable folders, with SHA-256 inventories and exported Premake
projects. Their identities describe exact exported bytes rather than a historical
chapter commit. The six Starter/Solution pairs keep their acceptance oracles
unchanged; the two complete checkpoints do not claim an incomplete Starter.

| Chapters | Content-addressed CPU checkpoints | Form |
| --- | --- | --- |
| 12, 16 | `ch12-hierarchy`, `ch16-lights` | Parent/child and light-foundation pairs on current reference code |
| 39 | `ch39-visibility-depth` | Complete production CPU visibility/depth oracle, for [Renderer convergence](RendererConvergence.md), step 2 |
| 42 | `ch42-integrated-drift` | The world wind's gust offset summed through a turn; the Starter puts velocity times time back |
| 43 | `ch43-numerics` | Complete small numerical bridge and production CPU-reference comparison |
| 45 | `ch45-bindings`, `ch45-hierarchy`, `ch45-documents` | Three pairs for typed access, hierarchy restoration and checked document edits |

Use the checkpoint guide to prepare, export, generate, build and check each
source set. A passed CPU checkpoint does not certify Vulkan execution, visual
appearance, performance or every intermediate state of the chapter.

Latest inspection follow-up: [CH48-grass-appearance](48-Grass-In-The-Coastal-Pipeline.md#ch48-grass-appearance)
separates sparse source admission, physical coverage and distance-lighting artifacts.
Its independent Starter/Solution builds, exact intended failures and RTX/Radeon
native smokes are verified. The [accepted Horizon checkpoint](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md#accepted-horizon-grass-checkpoint-2026-10-19)
records the preserved build, explicit inspection profile, measured lighting
cost and unfinished scope. Earlier paired source pins remain historical;
acceptance does not mean every original final-scene stage is implemented.

Verification evidence and limits: [REFERENCE.md](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md) and
[the native checks](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/README.md).

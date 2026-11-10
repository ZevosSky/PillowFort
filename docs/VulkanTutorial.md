# PillowFort Vulkan Tutorial

> **This is the `main` guide copy.** Build the growing lessons in your
> learning checkout. Named reference checks and prepared Starter/Solution
> commands run in a separate `reference-main` checkout, not in this scaffold.
> [Choose the correct source tree](BranchWorkflow.md) before running them.

A ground-up Vulkan refresher, written against **this** repository: its module
names, its Premake workspace, and the demos it exists to host.

[ROADMAP.md](../ROADMAP.md) says *what* the foundation is and *why*.
This tutorial is the missing *how* — the Vulkan concepts behind each checklist
item, with code that compiles against Vulkan 1.3 core. Read ROADMAP's
[Steps](../ROADMAP.md#steps) and [Guardrails](../ROADMAP.md#guardrails) before
you start: every chapter's header names its step, and the chapters cite the
Guardrails by number.

**Start:** [Chapter 1](Tutorial/01-Environment-And-Build.md), after
[the mental model, in one page](#the-mental-model-in-one-page) and
[what changed since the tutorials you probably remember](#what-changed-since-the-tutorials-you-probably-remember)
if your Vulkan is from the 1.0 era; or
[choose a later route](#choose-a-route-before-choosing-the-next-chapter).
**Returning after a break:** [pick up at a checkpoint](#work-in-checkpoints-and-leave-a-way-back).
**Checking a concept:** [primary sources and implementation boundaries](Tutorial/ConceptSources.md).
**Pages beside the chapters:** [reference pages and optional labs](#pages-beside-the-chapters).

---

## Who this is written for

Someone who has used Vulkan before, has not used it recently, and is going to
build these things:

| Demo | What it actually forces you to learn |
| --- | --- |
| Triangle + ImGui controls | Instance/device/swapchain/pipeline, push constants, CPU-to-GPU parameter flow |
| USD scene viewer | Cameras, depth, vertex and index buffers, a scene graph, a third-party library, materials, textures, lights, shadows, MSAA, instancing; then deferred shading, a sky, and light from the sky |
| Conway's Life | Compute pipelines, workgroups, storage images, barriers between dispatches |
| GPU particles | Storage buffers, atomics, compute-written indirect draws, timing the GPU |
| Grass, toward *Ghost of Tsushima* | GPU-generated instances, culling and LOD in compute, procedural blade shape, wind, and shading |
| Clouds | Marching rays through a volume, 3D noise images, a running average across frames |
| FFT ocean, then a rougher sea | Storage images, ping-pong dispatch, compute-to-graphics barriers; then cascades of FFTs, spray the GPU decides to emit, and a boat floated by a rigid body on the GPU |
| Path tracer | Storage-image accumulation, descriptor management, optionally acceleration structures and ray query |
| An island to the horizon | Level of detail, reversed depth, terrain rings over a heightmap, objects chosen by their size on screen, ground materials, leaf-card plants, impostors for the far forest, grass and sea composed on one coast, and shallow water running up a beach: one open world grown chapter by chapter |

You should be at home in C++20: designated initializers, `std::span`,
`std::format`, and RAII appear from Chapter 2 on without introduction.
Basic graphics and linear algebra are assumed: the raster pipeline, vectors,
dot and cross products, matrix composition, coordinate transforms and
perspective projection. The camera and mesh chapters include refreshers;
use them when needed. The required explanations focus on this renderer's
conventions, Vulkan's contracts, and the methods a later demo introduces.

Every chapter ends with an **exit check**: things to run, look at, or break on
purpose, each with what you should see. Chapters 2–4 build pieces that
nothing runs until Chapter 5's frame loop exists, so their runtime checks say
to do them after Chapter 5. From Chapter 5 on, every check is something you
run and observe. Each chapter's header names its step in
[ROADMAP.md](../ROADMAP.md).

---

## What you need, and what it teaches

### To build and run it

<a id="choose-your-checkout"></a>

**Which checkout.** Apply the growing chapter listings in a learning branch
made from `start`. Keep `reference-main`, the assembled project and
prepared-exercise support, in a separate checkout. `main` carries the guide
and scaffold. The
[branch workflow](https://github.com/ZevosSky/PillowFort-private/blob/main/docs/BranchWorkflow.md)
shows how to keep those source trees separate. A paired exercise names its
Starter; edits to the reference root do not test that Starter.

- **The `start` scaffold**, which the chapters write into. It initially holds
  `GenerateProjects.bat` and Premake (Chapter 1 wires them up), a placeholder
  `SandboxGame/Main.cpp` (Chapter 5 replaces it), the older
  `VulkanGraphics/Camera/` (Chapter 10 compares its own camera against it), and
  `ErrorReporting/Log.h`: three static functions, `Log::info`, `Log::warning`,
  and `Log::error`, each taking a `const char*`, which the chapters call as
  `Log::error(std::format(...).c_str())`. Everything else in `VulkanGraphics`
  is what Chapters 2–8 write. Those files already have assembled versions on
  `reference-main`; the initial-file description applies to the learning scaffold.
- **Windows 10 or 11, x64**, with **Visual Studio 2022** (the "Desktop
  development with C++" workload) and PowerShell. Premake is in the repository;
  Chapter 1 wires it up, and [Building with Premake](Premake.md) is a short
  guide to using it, other generators included.
- **The Vulkan SDK**, with `VULKAN_SDK` set, and its optional GLM and Vulkan
  Memory Allocator components selected when you install it (Chapter 1,
  section 1 says how to check). The code was checked against 1.4.357.
- **git**, for the submodules: GLFW and ImGui from Chapter 1, TinyUSDZ from
  Chapter 13.
- **A GPU and driver with Vulkan 1.3** — including dynamic rendering,
  synchronization2 and a `D32_SFLOAT` depth format that supports both attachment
  and sampled use. Chapters 2 and 10 query these capabilities and name what
  is missing. Later lessons add required anisotropic filtering (15),
  `multiDrawIndirect` and `drawIndirectFirstInstance` (19); query and enable
  those feature bits rather than inferring support from the GPU's age or API
  version. The [Vulkan feature contract](https://docs.vulkan.org/spec/latest/chapters/features.html)
  distinguishes support from enablement. The path tracer's route B (33) adds
  optional ray-query hardware/extensions; route A uses the engine's ordinary
  compute requirements. Chapter 43's shoreline enables
  `VK_EXT_conditional_rendering` where present, so the GPU's own adaptive
  step decides whether the solver's substeps run; without it, the same
  decision reaches the dispatches as indirect group counts.
- **Later, and optional:** Python 3 for the scripts that write test scenes
  (14–17, 19, 22, 23, 31) and the island, its materials and its plants
  (36–39), all of which, with what they write, are on the `start` branch under
  `Assets/`; Blender 4.5 to make your own USD scenes (14, 16); and RenderDoc,
  which Chapter 6's exit check asks for (Chapter 34, sections 1 and 2, with
  its [early-capture route](Tutorial/34-Debugging.md#early-capture-route), are
  a short walkthrough of it on this engine's frame; section 3 waits for
  Chapter 24).

### How long it is

Each group under [Chapters](#chapters) gives its length and what you have at
its end. The word counts include the code listings, and describe the
material, not a deadline. A chapter can span several work sessions. The long
chapters are split into parts inside one file; use their runnable checkpoints
as stopping points.

### The math you will meet

Basic graphics and linear algebra are prerequisites, rather than separate
learning goals. Existing vector, matrix and projection refreshers are optional;
the Vulkan clip/depth conventions and C++/GLSL layout contracts still need to
be checked even if you know the underlying math.

New methods are introduced where the demos need them. Chapters 29 and 33
develop complex numbers and the Fourier transform for the ocean, and
probability and Monte Carlo integration for the path tracer. Read those
primers before their implementation if the methods are unfamiliar. Chapter
43 starts with a small finite-volume calculation: one wet/dry
HLL face, the pressure balance of a still lake and a numerical CFL step. Its
CPU checkpoint compares that calculation with the reference solver. The full
second-order reconstruction and shoreline coupling remain larger extensions;
the opening arithmetic is a bridge to them, not a derivation of every scheme.

[The math, chapter by chapter](#the-math-chapter-by-chapter), in the
Reference section, lists every passage: use it to find one again, or to see
what is coming.

---

## Chapters

The chapters in reading order, in groups. A chapter's number is its name, not
its place in one build sequence: a side branch sits beside the chapter it
leaves from, and the planned chapter comes last. Read after names the
chapter to finish first; each chapter's Prerequisites list, in its header,
names the sections it uses.

**Foundation, 1–8.** About 48,000 words; you end with a triangle with live
ImGui controls, drawn through an HDR offscreen target. Chapter 8 has several
resource checkpoints.

| # | Chapter | Covers | Read after | Form | Step |
| --- | --- | --- | --- | --- | --- |
| 01 | [Environment and Build Wiring](Tutorial/01-Environment-And-Build.md) | SDK tour, the Premake workspace and when to regenerate it, linking the loader, GLFW and ImGui submodules, validation config | — | typed into your tree | 1 |
| 02 | [Instance, Device, and Queues](Tutorial/02-Instance-And-Device.md) | Layers, debug messenger, the window, feature chaining, queue family selection | 1 | typed; runtime checks after Chapter 5 | 3 |
| 03 | [The Swapchain](Tutorial/03-Swapchain.md) | Surface caps, format and present-mode choice, what sRGB is, recreation | 2 | typed; runtime checks after Chapter 5 | 4 |
| 04 | [Commands and Synchronization](Tutorial/04-Commands-And-Synchronization.md) | Pools, frames in flight, the semaphore trap, sync2 barriers | 3 | typed; runtime checks after Chapter 5 | 5 |
| 05 | [The First Frame](Tutorial/05-First-Frame.md) | Dynamic rendering, clear, present, resize survival | 4 | typed into your tree | 6 |
| 06 | [Shaders and Pipelines](Tutorial/06-Shaders-And-Pipelines.md) | `glslc` through tracked Premake custom-build rules, shader modules, the graphics pipeline, the triangle | 5 | typed into your tree | 7 |
| 07 | [ImGui Debug Panels](Tutorial/07-ImGui.md) | Backend init under dynamic rendering, manual input forwarding, the frame-statistics panel | 6 | typed into your tree | 8 |
| 08 | [Resources, Memory, and Descriptors](Tutorial/08-Resources-And-Descriptors.md) | Memory types, staging, images, the offscreen target and composite pass, descriptor sets, push constants, the ImGui-to-shader parameter path | 7 | typed into your tree | 9 |
| 34 | [Debugging and Profiling](Tutorial/34-Debugging.md) | RenderDoc on this engine's frame: taking a capture, reading the frame, finding our buffers by set, binding, and size; then GPU timing, reading validation messages, a lost device, object names and labels if you want them, a milestone checklist | 6, then in pieces (see [Routes](#routes)) | toolbox | all |

**ROADMAP step 2**, the GLFW window and frame loop, has no chapter of its own,
which is why the Step column skips it. Read it in four places, in this order:
Chapter 2, section 4 (the `Window` module's `GlfwWindow` and its event queue),
Chapter 7, section 4 (registering the input callbacks), Chapter 5, section 3
(the loop body), and Chapter 10, section 10 (where the window's later additions
go). Closing is polled through `shouldClose`, not queued as an event, although
ROADMAP step 2's checklist lists close among the queued events.

**Scenes and the shared renderer, 9–24.** 9–19, about 160,000 words: a USD
scene viewer with materials, lights, shadows, MSAA and instancing. 20–24, about
90,000 words: Life and GPU particles, then deferred shading, a sky and light
from the sky for every 3D demo. Life establishes dispatch and data
dependencies; particles add GPU-owned counts and timings; 22–24 apply both to
the scene renderer.

| # | Chapter | Covers | Read after | Form | Step |
| --- | --- | --- | --- | --- | --- |
| 09 | [The Demo Harness](Tutorial/09-Demo-Harness.md) | The `Demo` interface, explicit registration in `SandboxGame`, an ImGui demo switcher, per-demo resize; the triangle becomes the first demo | 8 | typed into your tree | 10 |
| 10 | [Cameras and Depth](Tutorial/10-Cameras-And-Depth.md) | Matrices, view and projection in Vulkan's clip space, fly and orbit controllers, the per-frame camera buffer, the depth buffer | 9 | typed into your tree | 11 |
| 11 | [Meshes](Tutorial/11-Meshes.md) | Vertex input state, interleaved vertices, index buffers, uploading mesh data, winding and culling, per-draw transforms, one light | 10 | typed into your tree | 12 |
| 12 | [The Scene Graph](Tutorial/12-Scene-Graph.md) | Nodes and transform hierarchies, dirty flags, flat draw lists, cameras as nodes, an ImGui hierarchy and inspector (engine work; 15–19 need it) | 11 | typed into your tree | 13 |
| 13 | [Adding a Library: TinyUSDZ](Tutorial/13-Adding-TinyUSDZ.md) | The recipe for any third-party library here, USD's core ideas, loading a stage (engine work; 15–19 need it) | 12 | typed into your tree | 14 |
| 14 | [Importing USD Scenes](Tutorial/14-Importing-USD-Scenes.md) | Prims to nodes, triangulation, primvars, up axis and units, USD cameras (engine work; 15–19 need it) | 13 | typed into your tree | 15 |
| 15 | [Materials and Textures](Tutorial/15-Materials-And-Textures.md) | `UsdPreviewSurface`, texture loading, mipmaps, samplers, per-material descriptor sets, tangents | 14 | typed into your tree | 16 |
| 16 | [Lights](Tutorial/16-Lights.md) | UsdLux lights as nodes, light buffers, forward shading, light units, exposure and tone mapping | 15 | typed into your tree | 17 |
| 17 | [Shadows](Tutorial/17-Shadows.md) | Shadow maps for the sun, depth bias and filtering, cascaded shadow maps for large outdoor views | 16 | typed into your tree | 18 |
| 18 | [Anti-Aliasing](Tutorial/18-Anti-Aliasing.md) | MSAA under dynamic rendering, resolve attachments, sample counts, alpha-to-coverage; what MSAA cannot fix | 17 | typed into your tree | 19 |
| 19 | [Instancing and Indirect Draws](Tutorial/19-Instancing-And-Indirect.md) | Per-instance storage buffers, USD instancing, indirect draw buffers; [sections 9–11](Tutorial/19-Instancing-And-Indirect.md#instancing-usd) (USD instancing, the forest) are optional on the [renderer route](#routes) | 18 | typed into your tree | 20 |
| 20 | [Compute Fundamentals](Tutorial/20-Compute-Fundamentals.md) | Compute pipelines, the execution model, storage buffers and images, barriers between dispatches | 19, or 10 on the ocean and path-tracer routes | typed into your tree | 21+ |
| 21 | [GPU Particles](Tutorial/21-GPU-Particles.md) | Emit and simulate in compute, atomics, compaction, compute-written indirect draws, blending, and completed GPU timestamp intervals for controlled comparisons | 20 | typed into your tree | 21+ |
| 22 | [Deferred Shading](Tutorial/22-Deferred-Shading.md) | A G-buffer, lighting in a compute pass with tiled light culling, a live switch between forward and deferred, and when each wins | 21 | typed into your tree | 21+ |
| 23 | [The Sky](Tutorial/23-The-Sky.md) | A sky behind every 3D demo, chosen in one engine setting: cube maps and their face order, lat-long environment images and USD dome lights, an analytic daylight sky from the sun, and the depth-1.0 trick that draws it last, forward and deferred (Horizon, in Chapter 35, draws it first under reversed depth) | 22 | typed into your tree | 21+ |
| 24 | [Image-Based Lighting](Tutorial/24-Image-Based-Lighting.md) | The sky as the scene's light: a diffuse cube and a specular cube with a level per roughness, filtered by compute whenever the sky changes, GGX's split-sum lookup table, Chapter 15's three BRDFs side by side, both of Chapter 22's paths, USD dome lights, and Chapter 21's timestamp queries made into a class | 23 | typed into your tree | 21+ |

**Side branches that come back.** Each leaves from a named chapter and comes
back; none is a prerequisite of a later numbered chapter, and none needs the
island: terrain, grass and water are later transfers, not prerequisites. Back
where you branched means 25 in number order, or 28 on the
[renderer route](#routes).
From Chapter 20 on every chapter is ROADMAP step 21+, so the tables from here
drop the Step column.

| # | Chapter | Covers | Read after | Form |
| --- | --- | --- | --- | --- |
| 45 | [Scene Documents And Typed Properties](Tutorial/45-Scene-Documents-And-Properties.md) | Versioned self-contained CPU scenes, explicit typed property reflection and viewer save/load; full procedural-world scene integration remains partial | 19 (it supplies the CPU environment data it borrows from 23); back to 20, following its return merge when you later add 22–23 | typed, with CPU checkpoints |
| 52 | [Wind Fields And Vorticles](Tutorial/52-Wind-Fields-And-Vorticles.md) | Independent local source lifetimes, compact finite velocity fields, checked snapshots and particle response | 21; back to 22. More labs: [Particle extensions](Tutorial/ParticleExtensions.md) | three problems over the assembled reference |
| 49 | [Bloom And Color Grading](Tutorial/49-Bloom-And-Color-Grading.md) | Linear HDR color order, a normalized bloom pyramid, real final-output capture and measured costs | 24 (or after 16 and 18, as its header says); back where you branched | problems; one prepared pair |
| 50 | [Screen-Space Ambient Occlusion](Tutorial/50-Screen-Space-Ambient-Occlusion.md) | Depth reconstruction, spatial AO/filtering and diffuse-only ambient integration in single-sample deferred lighting | 24, on 22's deferred path; back where you branched | problems; one prepared pair |
| 51 | [Atmosphere And Aerial Perspective](Tutorial/51-Atmosphere-And-Aerial-Perspective.md) | Units and optical depth, physical sky/lighting LUTs, finite-segment transport and stable water composition | 24, with 23's sky; back where you branched | problems; one prepared pair |

49, 50 and 51 are independent of each other; take any of them, in any order.

**After 24: grass, then clouds.** The grass (25–27, about 54,000 words, toward
*Ghost of Tsushima*) is optional: nothing on the renderer route depends on it.
The clouds (28, past 3,000 lines) are on the renderer route.

| # | Chapter | Covers | Read after | Form |
| --- | --- | --- | --- | --- |
| 25 | [Grass I: Blades](Tutorial/25-Grass-Blades.md) | Forty thousand blades on rolling ground, each a curved, tapered strip the vertex shader builds from two `vec4`s, with no vertex buffer; lit by Chapter 16's sun and shadowed by Chapter 17's cascades | 24 | typed, optional |
| 26 | [Grass II: GPU Generation](Tutorial/26-Grass-GPU-Generation.md) | An endless field generated around the camera every frame: compute culls, thins and appends blades into two levels of detail, drawn indirectly from GPU counts; optionally, culling against last frame's depth | 25 | typed, optional |
| 27 | [Grass III: The Look](Tutorial/27-Grass-Look.md) | Clumps, wind in gusts, blades that stay solid edge-on and never thinner than a pixel, rounded shading, light through the blades, a highlight, grass shadows and a ball that pushes the blades | 26 | typed, optional |
| 28 | [Clouds](Tutorial/28-Clouds.md) | Participating media and Beer-Lambert, a ray march into a cloud cube of its own drawn over Chapter 23's sky, Henyey-Greenstein and multiple scattering by octaves, tileable Perlin-Worley noise in 3D images, a weather map, wind, and time slicing with a running average | 27, or 24 with Chapter 27, sections 1 and 2 read first | typed into your tree |

**Entered from 20, with no return: the sea and the path tracer.** With the
clouds, 28–32 are about 117,000 words; 33 and 34 about 26,000. Neither route
needs the other. The sea is needed again only on the island's coast (41) and
by Renderer convergence's optional step 4.

| # | Chapter | Covers | Read after | Form |
| --- | --- | --- | --- | --- |
| 29 | [The FFT Ocean](Tutorial/29-FFT-Ocean.md) | Complex numbers and the FFT, a GPU FFT tested on single waves, Tessendorf's spectrum, foam from the Jacobian, water shading | 20; its Prerequisites name what it takes from 18 and 21 | typed into your tree |
| 30 | [A Rougher Sea](Tutorial/30-A-Rougher-Sea.md) | Three FFT cascades whose bands never overlap, JONSWAP beside Phillips with fetch, directional spreading and a crossing swell, foam that lingers across frames, the engine's sky and clouds reflected with a normalized glint, a skirt to the horizon | 29; its Prerequisites name what it takes from the sky (23) and the clouds (28) | typed into your tree |
| 31 | [Spray](Tutorial/31-Spray.md) | A rock in the sea, the water's height at a point by guess-and-correct, one probe set through which compute reads the sea, GPU-decided spray requests feeding Chapter 21's particles, a local foam map that does not repeat | 30 | typed into your tree |
| 32 | [A Boat](Tutorial/32-A-Boat.md) | Archimedes on hull columns, a rigid body moved on the GPU from the water it floats on, steering on the arrow keys, spray at the bow, a wake, a follow camera | 31 | typed into your tree |
| 33 | [Path Tracing](Tutorial/33-Path-Tracing.md) | Monte Carlo integration, a compute path tracer, accumulation, ray query and acceleration structures | 20; its Prerequisites name what it takes from 11, 15, 16 and 21 | route A typed; route B optional |

**The island world.** 35–39 are long typed chapters, 39 the longest in the
book; 40–43 are problems over the assembled reference, and 42 also prints
all the engine code it changes. You end with an
island seen to the horizon, with far forests, grass and sea on one coast and
gentle waves running up its shore; 46–48 add shared captured grass with a
projected handover.

| # | Chapter | Covers | Read after | Form |
| --- | --- | --- | --- | --- |
| 35 | [Seeing Far](Tutorial/35-Seeing-Far.md) | Why distance needs level of detail; test plates that show depth running out; how far apart floats are, and a 5 km travel limit; reversed depth inside one demo, with the sky drawn first | the renderer route; its Prerequisites name the sections it uses | typed into your tree |
| 36 | [Terrain to the Horizon](Tutorial/36-Terrain-To-The-Horizon.md) | Geometry-clipmap rings, first on noise, then on an eroded island's 16-bit heightmap; the sea around it, haze, a skirt to the horizon, and a ground clamp | 35 | typed into your tree |
| 37 | [Objects at a Distance](Tutorial/37-Objects-At-A-Distance.md) | The open world's first chapter: USD assets with three levels chosen by their height on screen; landmarks and villages; one forest-density function in GLSL and C++ and the near trees it plants; shadows near the camera; GPU timers and presets | 36 | typed into your tree |
| 38 | [Ground Materials](Tutorial/38-Ground-Materials.md) | A material map of six weights from the erosion script; far colours in patches faded by a pixel's footprint; six tiled CC0 photographs up close, meeting by height, with rock projected from three sides on cliffs | 37 | typed into your tree |
| 39 | [Plants](Tutorial/39-Plants.md) | Leaf-card plants grown after EZ-Tree in three levels; alpha test and alpha to coverage; a coverage scale per mip level; far trees' solid shadows; an overdraw view; an understory planted every frame by compute from the material map | 38 | typed into your tree |
| after 39 | [Renderer convergence](Tutorial/RendererConvergence.md) | Four architecture exercises after the plant work: one owner for mesh geometry; per-cascade shadow visibility and one depth convention; frames that fail before they are submitted; an optional shared FFT for the ocean and the sea. Between the second and third, a supplied section on the shared distance haze | 39's plant exit check; steps 1–3 before 40, step 4 only after 29–30 | typed problems with CPU checks; one prepared pair |
| 40 | [Forests to the Horizon](Tutorial/40-Forests-To-The-Horizon.md) | Impostors baked from Chapter 39's own trees as surfaces seen from many directions, lit live and writing depth; the same trees placed by world cell for both forms, exactly one form owning each tree, with hysteresis at the handover; what the cache and the whole forest cost | Renderer convergence, steps 1–3 | problems over the assembled reference |
| 41 | [Grass on the Island](Tutorial/41-Grass-On-The-Island.md) | A bounded coastal area where the grass (25–27) and the sea join the island in one frame: one camera, depth and shadow contract; blade roots on the triangles the rings actually draw; a habitat that keeps the beach bare; shadows from the bent blades | 40, with the grass (25–27) and the FFT sea (29–30) whole | problems over the assembled reference |
| 42 | [One Wind](Tutorial/42-One-Wind.md) | One wind for each demo, owned once and written into `FrameData` every frame. It replaces the grass's own wind and the coast's copy of the sea's (section 1), and turns without the gusts jumping: the gust offset summed frame by frame, the eased turn and **Guide toward** (section 2). The sea keeps its own wind; the trees, the understory, the far forest, their shadows and the clouds join it in 53 (planned) | 41; 43 does not need it | typed problems over the assembled reference; one prepared CPU pair |
| 43 | [Waves to the Shore](Tutorial/43-Waves-To-The-Shore.md) | Gentle long waves on one fixed coastal patch: a bed that does not move with the camera, shallow-water transport that keeps a lake still and conserves water as fronts wet and dry, a physical clock independent of frame rate, a boundary driven by the FFT sea's own spectrum, wet sand left behind, and the bed seen through the water. Breaking and surf are 44's. It opens with worked face-flux, lake-at-rest and CFL calculations | 41 | problems over the assembled reference |
| 46 | [Capturing Grass Clumps](Tutorial/46-Capturing-Grass-Clumps.md) | Actual procedural source, multi-view unlit capture, material coordinates and coverage-weighted mips | 27 and 41 | contract-led problems, named source pairs and worked answers |
| 47 | [Grass Representation Handover](Tutorial/47-Grass-Representation-Handover.md) | Stable source identity, projected transitions, explicit coverage, coherent deformation and reconstructed depth | 46 | contract-led problems, named source pairs and worked answers |
| 48 | [Grass In The Coastal Pipeline](Tutorial/48-Grass-In-The-Coastal-Pipeline.md) | Habitat admission versus opacity, shared-frame integration, per-view lighting and measured trade-offs | 47; its persistent-world problem also needs 43 | contract-led problems, named source pairs and worked answers |

**Planned, not written.**

| # | Chapter | Covers |
| --- | --- | --- |
| 44 | Surf and Sand (planned) | Breaking, foam, swash and wet sand; from afar, a white line along the coast and a glitter path from 12 wind ripples |
| 53 | Rolling Wind (planned) | Read after 42, over the grass clumps of 46–48. Gusts that roll across the island, as in *Ghost of Tsushima*: one gust field that travels with the wind, blades that lean to the gust that passed upwind a moment ago, a sheen where a gust passes; then trees that bend from the foot with their branches and leaves attached, the understory, the far forest, swaying shadows, and clouds on the world wind aloft |

Neither is a prerequisite of any written chapter; skip their numbers.

**The appendix.**

| # | Page | Covers | Read after |
| --- | --- | --- | --- |
| — | [The engine you built](#appendix-the-engine-you-built) | What owns what, one 3D frame in order, `FrameData` whole, and everything the book names but does not build | 34 (the far view's code lives in its `Horizon` demo) |

<a id="choose-a-route-before-choosing-the-next-chapter"></a>

### Routes

Chapter numbers identify lessons; they are not one build sequence. There are
two different prerequisites to check: **code already assembled** in your
working checkout, and **ideas to read** from another chapter. A section-only
reading dependency does not supply that chapter's classes or shader bindings.
Prepared exercises supply their own named support; use the stage's source
rather than assuming a historical checkout has it. Each chapter's
Prerequisites list is authoritative down to the section; this list names only
where a route enters and what it skips.

- **Renderer (1–24, then 28):** 1–24 in order, taking only sections 1–8 of
  Chapter 19; then 28, reading Chapter 27, sections 1 and 2 first if you
  skipped the grass. Chapters 12–14 are engine work rather than Vulkan (a
  scene graph and a USD importer), but 15–19 need them. The side branches
  leave from this route and come back to it, and the far-view island begins
  after it.
- **Ocean (29–32):** assemble 1–10 and 20, then take 29. If you skipped them,
  Chapter 29's Prerequisites name what it takes from Chapters 18 and 21 (the
  scene's sample count and the random helpers). You do not need the
  intervening scene, grass or sky implementations. 30 brings sky and cloud
  support, 31 particles and props, 32 the boat; check each handoff before
  continuing.
- **Path tracer (33):** assemble 1–10 and 20, then take 33's route A.
  Chapter 33's Prerequisites name the sections of 11, 15, 16 and 21 it reads
  or supplies. Route B needs what its own prerequisites name. Grass, sea and
  IBL are not required.
- **Far-view island (35–43):** 35–39 after the renderer route; then
  [Renderer convergence](Tutorial/RendererConvergence.md), steps 1–3, which 40
  requires; then 40, 41, 42, 43, where 43 does not need 42. Each chapter's Prerequisites name the sections of
  21 and 25–30 it uses. 41 needs the grass (25–27) and the FFT sea (29–30)
  whole. The sea is needed at the coastal handoff, not to begin the depth
  experiment.
- **Debugging (34):** sections 1 and 2, with the
  [early-capture route](Tutorial/34-Debugging.md#early-capture-route), at
  Chapter 6's exit check; section 5 for validation messages; section 3 after
  24 (its exercises name the resources they need); 6 for device loss; 7 for
  optional names and labels; 8 at a milestone. The
  [engine appendix](#appendix-the-engine-you-built) is the reference when you
  lose track of an owner or a pass.

Every other route follows the groups above: each row's Read after says where a
side branch enters and where it comes back.

### Where the code stands

Begin from `start` (see [Which checkout](#choose-your-checkout), under To
build and run it). When your version misbehaves, compare it first with the
chapter's worked answers and exit check; where a prepared stage exists for
your problem, compare with it, not with the final reference
([Reference solutions](Tutorial/ReferenceSolutions.md) marks each). The
catalog's [runnable support and evidence](Tutorial/ReferenceSolutions.md#runnable-support-and-evidence)
says which form of support each chapter has.

<details>
<summary>Optional comparison: what was built and run where</summary>

The assembled reference holds the code of the written chapters, with the
Windows pass's fixes. 44 and 53 remain planned; 45 implements scene
documents and properties while full procedural-world scene authoring remains
partial. The `start`
branch is where Chapter 1 begins. When your own version misbehaves, compare
it with the prepared stage for your problem, where one exists, not with the
final reference: the [stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md)
says which stages are paired exercises on the final reference and which are
true snapshots of the source at that chapter. Neither proves that every
intermediate listing was assembled on its own. The chapters show code as it
grows, and a source link can show later additions.

The [coverage matrix](Tutorial/ReferenceSolutions.md) distinguishes written
worked answers from the **21 Git-pinned paired exercises and 5 historical
snapshots**. A separate [CPU source catalog](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md)
adds five current-reference Starter/Solution pairs across scene foundations
and Chapter 45, plus complete Chapter 39 visibility/depth and Chapter 43
numerical checkpoints. These export independently buildable source sets with
content hashes; they are not historical chapter commits. Coverage of other
intermediate chapter states remains incomplete. Use each checkpoint's actual
checks instead of treating a modern demo switch or prose listing as an earlier
source build.

The bloom/AO pairs (49–50) pin reference commit `bbbe966`. Their independent
Debug Starter/Solution builds, both-GPU acceptance checks and all eight scene
smokes pass. Each Starter fails only its declared omission; Solutions keep all
healthy controls. Chapter 51 pins the focused physical-sky ground-boundary
revision `84b3b99`; both independent Debug builds, both-GPU acceptance and all
four scene smokes pass. All six exported variants have actual receipts; this
does not certify every intermediate listing. Reference runtime, scene
appearance and Release cost evidence remain separate in the roadmap.
`REFERENCE.md` records what was actually built and run:

**Accepted Horizon checkpoint, 2026-10-19:** The current grass appearance/
performance balance is preserved by an annotated source tag and native
snapshot; its source history is now integrated into `reference-main`.
[The checkpoint record](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md#accepted-horizon-grass-checkpoint-2026-10-19)
names its exact launch profile, verified lessons, local native snapshot and
remaining limitations. Chapters 27/41 identify superseded approximations;
46–48 teach the resulting coverage/lighting distinctions. Non-tiling ground
detail, tree-option changes and broader tutorial restructuring remain
subsequent work, not features silently added to this build.

- **1–8** were built with MSVC at `/W4` with no warnings and run
  validation-clean on Windows with a GPU, with sync validation proven live and
  the chapters' claims read back from GPU pixels.
- **9–33, and 35–39,** were built with g++ (from 35 also clang++) and run
  validation-clean on Linux (Mesa's lavapipe driver), with screenshots of
  their exit checks. `REFERENCE.md` says which have since had their run with
  MSVC on Windows and a GPU.
- **40, 41 and 43** were built with MSVC and run natively on Windows on an
  NVIDIA RTX and an AMD Radeon GPU, not on Linux. Their evidence is in
  `REFERENCE.md`'s dated sections ("Renderer Convergence And Forests",
  "Coastal Island Integration", "Shoreline Implementation"), not its
  per-chapter table.
- **42** was built with MSVC (v145, `/W4`, no
  warnings) and Vulkan SDK 1.4.363 and run natively on Windows: on an RTX
  5090, which gave every measured number in its text, and for a few shorter
  runs on a 2-CU AMD Radeon iGPU. Its evidence is in `REFERENCE.md`'s dated
  section "Chapter 42 One Wind, Sections 1 And 2".
- **34** has no engine code: it reads the engine as built, in RenderDoc and in
  the validation layer's messages, and leaves object names and labels to you
  (Chapter 34, section 7). Its walkthrough follows RenderDoc's own
  documentation.

The [roadmap](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/ROADMAP.md#graphics-systems-plan) records actual
implementation and verification gates; written lessons do not establish that
every intermediate listing was independently built. Existing chapter numbers
and historical source stages remain unchanged. The native regression checks
and their limits are documented in
[the verification harness](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/README.md).

</details>

---

## How to work through this

Do not read it all first. The value is in hitting each exit check before
moving on.

### Work in checkpoints, and leave a way back

Choose one attempt or runnable checkpoint for the current session. Read its
expected result before editing, predict what will change, then run the named
check. Chapters 2–4 have no frame loop yet: a compile or a written ownership
trace is the local checkpoint; their runtime checks become available in
Chapter 5. After Chapter 5, prefer a small observed result over finishing a
whole chapter.

When you stop, keep a short note beside your own work:

```text
Source/stage:       which checkout or prepared Starter I am editing
Last passing check: command, scene and relevant settings
Current problem:   attempt anchor; observed failure or unanswered question
Next action:       one concrete edit, inspection or experiment
```

Resume by opening that attempt and rerunning the last check. If it no longer
passes, resolve the changed starting state before adding the next feature.
Stopping with a recorded failure is a usable stopping point too.

Each chapter sets problems at its important milestones. Read the
prerequisites and concepts, then stop at an **Attempt**. Write a prediction or
implement the missing behavior, and run its acceptance checks. Keep the three
hints and the worked answer closed until you need them. The hints progress
from the governing idea to data flow to implementation details; use the next
one when you cannot name a productive next experiment. The worked answer is
always there to open, because the goal is a real attempt, not guessing
indefinitely: if you open it, identify the missing idea, close it, and try
the change yourself. After your version passes, change the input as the
problem's **Transfer** paragraph says and explain why it still works;
rereading the answer alone does not establish that.

[Reference solutions](Tutorial/ReferenceSolutions.md) indexes these attempts.
The collapsed worked listings solve that stage, while source links show the
assembled current reference, including later chapters. A later reference file
is a comparison, not something to paste wholesale into an earlier chapter.
Chapter 21's optional soft-particle exercise (section 9) also has a compiled,
runnable solution, in the Particles demo.

Finish one problem, its transfer check included, before adding the next
system. Keep four kinds of evidence separate: mathematical and data
contracts, native Vulkan execution, inspected appearance, and Release timing.
Passing one does not establish the others.

Where a chapter asks you to hold an idea the previous chapter did not prepare
you for, it says so in a box marked **Jump**, with what to keep in your head.
Those are the places to slow down.

**Run Debug with validation on, always.** A Vulkan bug caught by a validation
message costs two minutes. The same bug caught by a black screen costs an
afternoon.

---

## The mental model, in one page

Vulkan is not a rendering library. It is a specification for *driving a
queue-based coprocessor*, and almost everything in it falls into five ideas.

**1. Everything is create-info, then handle, then destroy.**
The API makes object lifetime explicit. You fill a `Vk*CreateInfo`
struct, call `vkCreateX`, get an opaque handle, and are personally
responsible for calling `vkDestroyX` before the device dies, in an order that
respects dependencies. `sType` is always the first member and always must be
set; `pNext` is how the API grew without breaking ABI.

**2. Track parent handles, ownership and use dependencies separately.**

```text
Loader (vulkan-1.dll)
+-- VkInstance                 -- API version, layers, instance extensions
    +-- VkSurfaceKHR           -- a platform window, wrapped
    +-- VkPhysicalDevice       -- enumerated GPU; borrowed, not created/destroyed by you
        +-- VkDevice           -- created from that physical device
            +-- VkQueue        -- where work is submitted (never created or destroyed by you)
            +-- VkSwapchainKHR -- the ring of presentable images
            +-- VkImage / VkBuffer / VkDeviceMemory
            +-- VkPipeline / VkPipelineLayout / VkDescriptorSetLayout
            +-- VkCommandPool -> VkCommandBuffer
```

The surface is not the device's parent. It is used when checking presentation
support and creating a swapchain. The application owns the created objects;
the diagram alone does not supply cleanup. Keep each resource alive until its
submitted users finish, then destroy it before the parent handle it needs.
Borrowed queues and enumerated physical devices have no matching destroy call.

**3. Recording a GPU command does not execute it.**
`vkCmd*` functions *record* into a command buffer. Recording is single-threaded
per command buffer, and command buffers from different command pools can be
recorded on different threads at once; a pool and every buffer allocated from
it belong to one thread at a time. Submitting with `vkQueueSubmit2` makes the
recorded work eligible to execute; submission is asynchronous, so the CPU can
continue while the GPU is still using those resources.

**4. Synchronization is entirely yours, and it has exactly three jobs.**

- **Execution dependency** — the specified consumer stages wait for the
  specified producer stages; this is not a blanket pause of the whole GPU.
- **Memory dependency** — writes become *available* and then *visible* to the
  accesses named by the dependency. Stage and access masks describe that
  contract, rather than prescribing a particular hardware cache operation.
  Noncoherent mapped CPU memory also needs its separate flush/invalidate rules.
- **Layout transition** — an image changes to the layout required by its next
  use; the driver may also change its internal representation.

A barrier can express these dependencies together; buffer barriers have no
image layout transition. Choose the producer and consumer scopes deliberately
rather than assuming a barrier serializes every access. The primitives:

| Primitive | Synchronizes | Typical use |
| --- | --- | --- |
| `VkFence` | GPU to CPU | "is frame N's command buffer done, so I can reuse it?" |
| Binary `VkSemaphore` | GPU queue to GPU queue | swapchain acquire / present handoff |
| Timeline `VkSemaphore` | GPU and CPU, many waiters | frame pacing, compute-to-graphics chains (not used in this tutorial) |
| Pipeline barrier | Selected earlier/later stages and accesses on one queue | layout transitions, compute ping-pong |
| Queue family ownership transfer | Between queue families | only if you add a dedicated transfer or compute queue |

**5. The GPU has no idea what your data means.**
A `VkBuffer` is a length and some usage flags. A `VkImage` is dimensions, a
format, and usage flags. Shaders reach them through **descriptors** (bound in
sets), **push constants** (inline, tiny, fast), or **device addresses** (a raw
64-bit pointer, the modern option, which Chapter 33, section 6 uses). Getting
data to a shader is a solved-once problem — solve it deliberately in Chapter
8 and every demo after it gets easier.

---

## What changed since the tutorials you probably remember

If your Vulkan memories are from the 1.0/1.1 era, roughly a third of the
boilerplate you remember is now optional or obsolete. This repo targets
**Vulkan 1.3 core**, which is where the good parts landed.

| You remember | Do this instead | Why |
| --- | --- | --- |
| `VkRenderPass` + `VkFramebuffer` + subpasses | **Dynamic rendering** via `vkCmdBeginRendering` and `VkRenderingInfo` | Deletes two object types; a pipeline states its attachment formats directly instead of naming a compatible render pass. Core in 1.3. |
| `vkCmdPipelineBarrier`, `VkSubmitInfo` | **Synchronization2** via `vkCmdPipelineBarrier2`, `vkQueueSubmit2` | 64-bit stage and access masks, per-barrier stages, far fewer "which stage do I use" mistakes. Core in 1.3. |
| Baked viewport and scissor in the pipeline | `VK_DYNAMIC_STATE_VIEWPORT` and `VK_DYNAMIC_STATE_SCISSOR` | Pipeline survives window resize instead of being rebuilt. |
| A descriptor set written for every draw | Push constants for small per-draw data; sets grouped by how often they change — once per frame, once per material (Chapter 8, section 6) | Few sets, each written when its contents change rather than per draw. Descriptor indexing and buffer device addresses exist for when sets get in the way; in this book only the path tracer's route B needs one, a device address. |
| `vkGetPhysicalDeviceFeatures` | `vkGetPhysicalDeviceFeatures2` with `VkPhysicalDeviceVulkan1{1,2,3}Features` | One struct per API version instead of one per extension. |
| Fence per frame + `renderFinished` semaphore per frame | Fence per frame **in flight**, `renderFinished` semaphore per **swapchain image** | The classic per-frame present semaphore is a genuine validation error. Chapter 4 explains it. |
| Hand-rolled `vkAllocateMemory` per resource | Vulkan Memory Allocator | Ships with your SDK, as an optional component. Chapter 8 shows allocation by hand once (read, not typed), then switches. |

Things that exist but that you should *not* reach for yet:
`VK_EXT_shader_object`, graphics pipeline libraries, mesh shaders,
`VK_EXT_descriptor_buffer`, and multi-queue async compute. Each is a real win
later and a distraction now. The closing appendix lists them with everything
else the book names and does not build.

---

## Reference: decisions every chapter relies on

The sections below are decided once and used by many chapters. Skim them now,
so you know they exist; the chapters link back here when they need them, and
each row names the chapter that teaches it.

### Pages beside the chapters

These pages sit beside the chapters, not in their reading order. A reference
page is for looking something up; an optional lab adds work the chapters do
not need; a companion belongs to one chapter.

| Page | Kind | Open it when | Sent from |
| --- | --- | --- | --- |
| [Reference solutions](Tutorial/ReferenceSolutions.md) | Reference | You are stuck at an attempt, want to see which problems have a prepared Starter, or are about to run one ([Working a prepared exercise](Tutorial/ReferenceSolutions.md#working-a-prepared-exercise)) | This page; every chapter with a prepared pair |
| [Concept sources](Tutorial/ConceptSources.md) | Reference | You want a concept's primary source, and what that source does not cover | The Start line above; the Sources sections of 15–17, 22–33 and 35–39 |
| [Reference images](Tutorial/ReferenceImages.md) | Reference | You compare a later output: each image comes with a question to inspect, and its caption separates historical diagnostics from the composed renderer and its numerical checks. It also lists the screenshots in the chapters | 6, 16, 21, 29, 30, 46 and 48–51 |
| [Building with Premake](Premake.md) | Reference beside Chapter 1 | You use Premake day to day, or want another generator | 1; [To build and run it](#to-build-and-run-it) |
| [Scene documents reference](Tutorial/SceneDocumentsReference.md) | Chapter 45's companion | You need 45's setup, its design comparison or its build recipes | 45 |
| [Particle extensions](Tutorial/ParticleExtensions.md) | Optional labs | You want more particle work, after 21 or 52; [Choose by mechanism](Tutorial/ParticleExtensions.md#choose-by-mechanism) picks a lab | 21 and 52 |
| [Foliage batches](Tutorial/FoliageBatches.md) | Optional lesson | You have built Chapter 39, section 10's understory and step 1 of [Renderer convergence](Tutorial/RendererConvergence.md#convergence-geometry), which writes `BuildMeshCommands`, and want to trace two plant sizes through its draws | 19, 37, 38, 39 and 49; Renderer convergence |
| [Branch workflow](https://github.com/ZevosSky/PillowFort-private/blob/main/docs/BranchWorkflow.md) | Reference | You set up the checkout you will edit, before Chapter 1 | [Which checkout](#choose-your-checkout) |

[Renderer convergence](Tutorial/RendererConvergence.md) is a lesson, not a
side page: the island world's group under [Chapters](#chapters) lists it
between 39 and 40.

### Conventions every chapter uses

From Chapter 9 on, the chapters do these things the same way. Each is said
once, here or in the chapter named, and a chapter that relies on one points
here instead of saying it again.

**Barriers come from three questions.** Chapter 4, section 5 decides every
barrier by what wrote, what reads, and in which layout. The common ones are
rows of its [cookbook](Tutorial/04-Commands-And-Synchronization.md#barrier-cookbook)
and of its [appendix of later barriers](Tutorial/04-Commands-And-Synchronization.md#appendix-barriers-the-later-chapters-add).
A chapter that needs one names the row and says only what differs. A barrier
is argued in full only when it is a new case: an atomic, an array of
descriptors, a chain through an earlier scope, a host fence wait, an image
that must keep its contents.

**A quiet validation layer proves nothing until a control has fired.** Run
Debug with validation on, always. Chapter 5's exit check fires the first
positive control, and Chapter 2, section 2 turns on the setting without which
sync validation ignores reads and writes through descriptors. A chapter that
adds a barrier gives its own control: weaken one line, see the named hazard,
put the line back. The retained controls report limitations of their recorded
SDK/layer version: atomics count as reads (20, 26), a read through an array of descriptors
(30), a second scope that loads the same image (21), a ping-pong's
write-after-write behind a read (Chapter 29, section 5), a hazard across the
tested host-fence wait (Chapter 36, section 8), and the vertex input of an
indirect draw (Chapter 39, section 9). These are not permanent claims about
every newer layer. Current [SyncVal documentation](https://github.com/KhronosGroup/Vulkan-ValidationLayers/blob/main/docs/syncval_usage.md)
includes fence/semaphore/wait-idle synchronization support while separately
listing missing host-memory race and indirect-data tracking. Repeat a control
after changing the layer, and retain its version with the result.

**Exit checks list what the checkpoints did not.** A chapter's exit check gives
its positive controls, its failure paths, and the numbers you compare. Every
exit check from Chapter 9 on also assumes the same hygiene, which it does not
repeat: validation silent (at 1x, and from Chapter 18 at 4x MSAA), a resize, a
switch to another demo and back, and a clean quit (VMA's `vmaDestroyAllocator`
asserts on a demo that leaks, Chapter 9, section 5). Chapter 34, section 8 is
the longer list for a milestone.

**A demo is Chapter 9's.** The `Demo` interface (Chapter 9, section 2), what a demo
is handed (Chapter 9, section 3), a panel through `beginDemoPanel` (Chapter 9, section 6), and
one line of registration in `SandboxGame` (Chapter 9, section 7). The appendix of
Chapter 9, a minimal demo whole, is the template every later demo starts
from. A later chapter prints its demo's new members, any `Setup` order that
matters, and what its `Teardown` does beyond the reverse of `Setup`.

**Descriptor sets.** Chapter 8, section 6 teaches the layout, the pool and the
set, and that a pool is counted by its layout: a clean run on one GPU proves
nothing (Chapter 24, section 3 is the case that taught it). Chapter 20, section 4
writes the recipe once more and makes it a helper. From there on a chapter
prints its binding table and the call, plus any line that is new.

**Uploads.** A buffer through a staging buffer is Chapter 8, section 2. An
image with its mip chain blitted from the top level is Chapter 15, section 5;
Chapter 36, section 8 and Chapter 38, section 2 show only what differs.

**Time on the GPU.** Chapter 21, section 8 teaches timestamp queries and
Chapter 24, section 9 makes them a class. Milliseconds measured on one machine
do not carry to another, so a chapter says what to measure and which way each
change moves it.

**Regenerate after adding a file.** Adding, renaming, moving or deleting a
source or shader file means rerunning `GenerateProjects.bat` (Chapter 1, section 3 says why). A chapter that adds files says "regenerate, then build".

**Where the measured numbers live.** The numbers the reference build measured
(milliseconds, pixel readings, counts) are in `REFERENCE.md` on the
`reference-main` branch, one row per chapter through 39; 40–43 keep theirs
in its dated sections. The text keeps the method, the direction of each
effect, and the numbers its exit check asks you to compare.

**Files you do not type.** The scripts that write test scenes, the island, its
materials and its plants are on the `start` branch under `Assets/`, and the
glTF converter and the tree it made under `ThirdPartyScenes/`, with the files
they write, identical to `reference-main`'s. A chapter prints the part of a
script it teaches and a table of what the file makes, and says how to run it.

**How code is shown.** Read the placement label before applying a listing.
Short new functions are usually printed whole. Longer functions and files
can span several fences; their continuation instructions identify the scope
left open and where its body or namespace closes. A single partial fence is
not a standalone source file. When a function grows, the chapter names the
edit location ("after the line that ...", "in place of ..."); apply that edit
inside the existing scope rather than appending a second definition.
Code you type sits at the paragraph that uses it. An appendix reprints a file
or function whole when several sections built it, so you can check yours
against it, or prints a script or test scene. A chapter's header lists what
it builds on: the previous chapter, built and running, and one line for each
earlier idea it uses without teaching it again, with its section. Chapters 40, 41 and 43 are the exception: they print only what a
worked answer needs and link the rest of the code from a table of the files
each changes. Chapter 42 also works over the assembled reference, but it
prints all the engine code it changes and links only its two new test files.

<a id="resource-owner-identity"></a>

**Resource owners keep their identity.** Classes that initialize and tear down
GPU/window/UI resources explicitly reject copying. They also suppress implicit
shallow moves; no current caller needs to relocate these owners. Construct them
in place and call their lifecycle methods. Teardown clears released handles and
state directly rather than assigning a fresh owner over the old one. Borrowed
contexts/targets and CPU scene/settings values retain their own copy semantics.
The upload helpers also use copyable buffer/image handle records: copying one
aliases the same GPU resource and still requires exactly one release. Moving
a plain handle record does not automatically null its scalar handles; the
helper's publication/cleanup protocol establishes who releases them.

**Running `Horizon` (35–43, 48).** Chapter 35, section 1 says how: the sky on,
click the scene before keys reach the demo, and the mouse turns the camera.

**Prepared exercises.** Through Chapter 39 you type into your own tree; a few
problems from 37 on also have a prepared Starter/Solution pair. From Chapter
40 on, most chapters are problems over the assembled reference (45, typed with
CPU checkpoints, is the exception): work in that checkout or in a prepared
Starter. [Reference solutions](Tutorial/ReferenceSolutions.md) marks which
problems have one, and
[Working a prepared exercise](Tutorial/ReferenceSolutions.md#working-a-prepared-exercise)
says how to run it. The other problems have worked answers and linked source,
and a chapter's source link does not establish that its intermediate stages
were independently built.

### SandboxGame's command line

`SandboxGame.exe` reads its settings as `--name value` pairs, in
`parseSettings` in `Source/SandboxGame/Main.cpp`. Every flag takes exactly one
value, so a switch is written `--bloom 1`, and an odd number of arguments
stops the program. An unknown flag is reported and ignored; most values
outside their range stop the program with a message that names the limits.
Values without a default below start empty or off.

The Where column names the chapter that teaches a flag or the setting it
sets. A flag marked *harness* exists in the assembled reference for scripted
runs and the [verification harness](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/README.md); no
chapter asks you to type it into your own `Main.cpp`, and a chapter that uses
one in a command names what it does there.

**Choosing the GPU, the demo and the scene.**

| Flag | Values (default) | What it sets | Where |
| --- | --- | --- | --- |
| `--gpu` | part of a device name | The GPU whose name contains it, as Chapter 2, section 5 chooses between two | Chapter 5, section 3 |
| `--present` | `fifo` (default), `fifo-relaxed`, `mailbox`, `immediate` | The present mode. An unknown name, or a mode the surface lacks (Chapter 3), falls back to FIFO with a warning | Chapter 5, section 3 |
| `--demo` | part of a demo's name | The demo to start on: the first whose name contains it, or the first demo | Chapter 9, section 7 |
| `--scene` | a file in `Assets/Scenes`, or a path | The USD viewer's first scene | Chapter 14, section 9 |
| `--msaa` | `1` (default), `2`, `4`, `8` | The scene's sample count, lowered to what the GPU offers | Chapter 18, section 3 |
| `--width`, `--height` | 320-7680 and 240-4320 (1280 × 720) | The window's size at startup | *harness*; used in 42, 48 and 49 |

**Bounded and scripted runs.**

| Flag | Values (default) | What it sets | Where |
| --- | --- | --- | --- |
| `--frames` | a count (0: run until closed) | Exits after that many frames. The captures below need it | *harness*; used in 42 and 48–50 |
| `--fixed-dt` | seconds, 0-0.1 (0: the real clock) | A fixed time step, so an animated frame repeats from run to run | *harness*; used in 42, 48 and 50 |
| `--capture` | a `.bmp` path | After the last frame, the resolved HDR scene, tone-mapped again on the CPU, before the UI: no bloom and no grading | Chapter 49, section 2 |
| `--capture-output` | a `.bmp` path | After the last frame, the bytes the composite actually wrote, before the UI | Chapter 49, section 2; used in 42 |
| `--capture-ui` | a `.bmp` path | After the last frame, the whole frame with the UI | *harness* |
| `--sequence` | a folder | The scene as one BMP per frame over an interval, at most 600 images; not with `--benchmark` | *harness*; used in 42 |
| `--sequence-first`, `--sequence-last`, `--sequence-every` | frame numbers (1; 0 means `--frames`; 1) | The interval and the stride of `--sequence` | *harness*; used in 42 |
| `--benchmark` | a `.csv` path | CPU and GPU timings, one row per frame after the warmup | Chapter 50, section 7; Chapter 51, section 7 |
| `--warmup` | frames (60) | How many frames `--benchmark` skips | *harness* |
| `--cycle-every` | frames (0: off) | Switches to the next demo every that many frames | *harness* |
| `--resize-at` | a frame number | Resizes the window to 1100 × 650 at that frame | *harness* |
| `--msaa-at` | a frame number | Switches to 4x MSAA at that frame, or to the GPU's largest count if it is lower | *harness* |
| `--ui-scale` | 0.75-3 (0: the window's content scale) | The UI scale, Chapter 7, section 5's live scale | *harness*; used in 48 |
| `--ui-scale-at` | a frame number | Applies `--ui-scale` at that frame instead of at startup | *harness* |
| `--ui-section` | `scene` (default), `render`, `stats` | The sidebar category of the assembled reference's workspace, Chapter 9's optional transfer (after its exit check) | *harness* |
| `--ui-controls` | `0`, `1` (1) | Hides or shows that sidebar's controls | *harness* |

**The picture: sky, tone and post-processing.**

| Flag | Values (default) | What it sets | Where |
| --- | --- | --- | --- |
| `--sky` | `off` (default), `sun`, `environment`, `atmosphere` | The engine's one sky setting | Chapter 23, section 8; `atmosphere` from Chapter 51 |
| `--clouds` | `0`, `1` (1) | The clouds, whenever a sky is on | Chapter 28 |
| `--exposure` | stops, -10 to 10 (0) | Exposure before the tone curve | Chapter 16, section 6; used in 49 and 50 |
| `--tone-curve` | `raw` (default), `aces`, `reinhard` | The tone curve | Chapter 16, section 6; used in 49 and 50 |
| `--bloom` | `0`, `1` (0) | Bloom | Chapter 49 |
| `--bloom-threshold`, `--bloom-knee` | 0-64000 (1, 0.5) | Bloom's soft threshold | Chapter 49, section 3 |
| `--bloom-strength`, `--bloom-levels` | 0-2 (0.08); 1-6 (5) | How much bloom is added, and over how many pyramid levels | Chapter 49, section 4 |
| `--grade-gain` | `r,g,b`, each 0-16 (`1,1,1`) | The grade's gain per channel | Chapter 49 |
| `--grade-saturation` | 0-2 (1) | The grade's saturation | Chapter 49 |
| `--graphics-fixture` | `black`, `constant`, `impulse`, `patches` (default) | The Graphics tests demo's picture | Chapter 49, section 2 |
| `--graphics-radiance` | 0-64000 (4) | That picture's radiance | Chapter 49, section 2 |
| `--atmosphere-density` | 0-4 (1) | The physical atmosphere's density | Chapter 51 |
| `--atmosphere-distance` | metres, 1000-200000 (200000) | The longest distance aerial perspective covers | Chapter 51 |
| `--atmosphere-multiple` | `0`, `1` (1) | Multiple scattering | Chapter 51 |

**The USD viewer, the particles and the path tracer.**

| Flag | Values (default) | What it sets | Where |
| --- | --- | --- | --- |
| `--render-path` | `forward` (default), `deferred` | The USD viewer's path | Chapter 22; used in 42 and 50 |
| `--ao` | `0`, `1` (0) | Screen-space AO. It needs the USD viewer, `--render-path deferred` and `--msaa 1` | Chapter 50, section 4 |
| `--ao-radius`, `--ao-strength` | metres, 0.01-10 (0.6); 0-2 (1) | The AO radius and strength | Chapter 50, section 4 |
| `--ao-view` | `lit` (default), `raw`, `filtered` | What the AO view shows | Chapter 50, section 4 |
| `--soft-distance` | metres, 0-1 (0: off) | The particles' soft-intersection distance | Chapter 21, section 9 |
| `--path-route` | `0` (route A, default), `1` (route B) | The path tracer's route | Chapter 33; route B in section 6 |

**Horizon.**

| Flag | Values (default) | What it sets | Where |
| --- | --- | --- | --- |
| `--horizon-view` | a viewpoint's name, such as `Coast` or `Forest floor` | Starts at one of the panel's viewpoints | *harness*; used in 42 and 48 |
| `--horizon-route` | `edge-sweep`, `aerial-orbit`, `forest-run`, `coast-walk`, `coast-orbit`, `coast-rim` | A scripted flight | Chapter 40, [CH40-measure-the-whole-forest](Tutorial/40-Forests-To-The-Horizon.md#ch40-measure-the-whole-forest) |
| `--horizon-world` | `integrated` (default), `legacy` | The persistent coastal world, or the older isolated one | Chapter 48, [CH48-persistent-world](Tutorial/48-Grass-In-The-Coastal-Pipeline.md#ch48-persistent-world) |
| `--horizon-view-cycle-every` | frames (0: off) | Visits the six bookmarks in turn and checks that the world survives | Chapter 48, [CH48-persistent-world](Tutorial/48-Grass-In-The-Coastal-Pipeline.md#ch48-persistent-world) |
| `--far-forest` | `0`, `1` (1) | The far forest | Chapter 40 |
| `--impostor-rebake` | `0`, `1` (0) | Bakes the impostors again instead of reading the cache | Chapter 40 |
| `--leaf-decorrelation` | `0`, `1` (1) | **Decorrelate coarse samples** | Chapter 39, section 6 |
| `--leaf-overlap` | 1-8 (1) | A diagnostic: that many layers per leaf plate, each a turned or mirrored copy of the picture | *harness* |
| `--shadow-culling` | `0`, `1` (1) | Per-cascade caster culling | [Renderer convergence](Tutorial/RendererConvergence.md), step 2 |
| `--shadow-stabilize` | `0`, `1` (1) | Shadow stabilization, Chapter 17, section 12's idea | *harness* |
| `--shadow-distance`, `--shadow-reach` | metres, 10-500 and 0-500 (Horizon's own) | How much view depth receives shadows, and how far towards the sun past each cascade a caster still casts (Chapter 17, section 2's `maxDistance` and `casterReach`) | Chapter 37 |
| `--coast-grass`, `--coast-sea`, `--coast-flow` | `0`, `1` (1 each) | The coast's grass (41), its sea (41) and its shoreline flow (43) | *harness*; `--coast-sea` used in 48 |
| `--coast-water-view` | `water` (default), `elevation`, `depth`, `speed`, `wetness` | The Coastal view selector: what the coastal water shows | Chapter 43, in its Files And Experiments |
| `--coast-grass-reach` | metres, 12-200 (42) | How far the coastal grass reaches | Chapter 48 |

**Grass, in the Grass demo and on Horizon's coast.**

| Flag | Values (default) | What it sets | Where |
| --- | --- | --- | --- |
| `--grass-view` | `near` (default), `grazing`, `aerial`, `transition` | The Grass demo's camera | Chapter 47, [CH47-projected-handover](Tutorial/47-Grass-Representation-Handover.md#ch47-projected-handover) |
| `--grass-route` | `none` (default), `traverse`, `orbit` | A scripted Grass demo camera | Chapter 47, [CH47-projected-handover](Tutorial/47-Grass-Representation-Handover.md#ch47-projected-handover) |
| `--grass-impostors` | `0`, `1` (1) | The captured-clump proxies, in either demo | Chapter 47 |
| `--grass-geometry-pixels`, `--grass-proxy-pixels` | pixels: proxy+1 to 80 (32); 2-40 (12) | The screen sizes of the handover from blades to proxies | Chapters 47 and 48 |
| `--grass-shadows` | `0`, `1` (1) | Grass shadows | Chapter 48 |
| `--grass-surface` | `legacy`, `filtered`, `blades` (default) | The grass's surface model | Chapter 48 |
| `--grass-source` | `legacy` (default), `patches` | The clump source layout | Chapter 48 |
| `--grass-work-span` | `1`, `4` (4) | Fine cells per coarse work cell | Chapter 48, [CH48-coarse-work](Tutorial/48-Grass-In-The-Coastal-Pipeline.md#ch48-coarse-work) |
| `--grass-debug-view` | `shaded` (default), `strip`, `normals`, `lod`, `tiles`, `clumps`, `wind`, `edge-on`, `coverage`, `albedo`, `ambient`, `diffuse`, `transmission`, `specular`, `occlusion` | A debug view of the grass | Chapters 25–27 and 48 |
| `--grass-flat` | `0`, `1` (0) | Flattens the Grass demo's ground | *harness* |
| `--grass-wind` | 0-1 (0.6) | The Grass demo's world-wind gust strength (Chapter 42, section 1) | *harness* |
| `--wind-turn-at`, `--wind-turn-to` | a frame number (0: never); degrees, -360 to 360 | At that frame, sets **Blows toward** in the Grass and Horizon demos, as a drag would; from Chapter 42, section 2 the wind turns there at its turn rate | Chapter 42, section 1 |
| `--wind-guide` | `none` (default), `lighthouse`, `tower`, `keep`; needs `--wind-turn-at` | At that frame, sets Horizon's **Guide toward** | Chapter 42, section 2 |
| `--grass-sun-elevation`, `--grass-sun-azimuth` | degrees, 1-90 (35); 0-360 (230) | The Grass demo's sun | *harness* |

### The math, chapter by chapter

Mathematical methods and convention checks, in reading order. Basic linear
algebra entries are refreshers, not additional prerequisites to learn here.
Use this table to find a renderer-specific convention or an unfamiliar method.

| Math | What it is for | Taught in |
| --- | --- | --- |
| Vectors: adding, scaling, length, normalizing | Positions, directions, colors | Assumed |
| The sRGB curve, and why light is added in linear | Every color you store or display | Chapter 3, section 2, with numbers; Chapter 8, section 4, the exact formula |
| Clip space, and values blended across a triangle | Where a vertex lands; the triangle's gradient | Chapter 6, section 2 |
| Blending two values by a fraction: linear interpolation, `mix` | The sRGB curve's two pieces; later, everything that fades | Chapter 8, section 4 |
| Byte layout: alignment and padding (`std140`, `std430`) | Structs shared between C++ and shaders | Chapter 8, section 8 |
| A matrix times a point; its columns as where the axes land; composing right to left; `w = 1` points and `w = 0` directions | Moving things, cameras | Chapter 10, section 1 |
| Perspective projection, read one row at a time; the divide by `w`; depth precision | The camera's picture | Chapter 10, section 2 |
| Quaternions, used as a tool | Orientations | Chapter 10, section 3 |
| The inverse of a matrix | The view matrix | Chapter 10, section 4 |
| Yaw and pitch from `sin` and `cos` | Fly and orbit cameras | Chapter 10, section 6 |
| The cross product | Normals, which side is the front | Chapter 10, section 8; applied in Chapter 11, section 4 |
| Winding seen on screen | Back-face culling | Chapter 11, section 7, as pictures |
| Transpose; the normal matrix (inverse transpose); a rotation's transpose as its inverse | Normals under non-uniform scale | Chapter 11, section 13 |
| The dot product as a cosine: Lambert's law | Diffuse light | Chapter 11, section 14 |
| A column's length as its scale; the cross product in components; handedness; the determinant as a mirror test; the dot product with a unit vector as how far along it reaches, and Gram-Schmidt: making one direction perpendicular to another | Taking a matrix apart; a camera's frame | Chapter 12, section 5, building on Chapter 10, sections 1 and 8 |
| A plane as four numbers; a matrix's rows read as planes; the frustum from a matrix | Culling | Chapter 12, section 10, building on Chapter 10, section 2 |
| Changing up axis and units with one matrix | Z-up and centimetre scenes | Chapter 14, section 2 |
| Row vectors and column vectors, and how the 16 numbers are stored | Reading USD's transforms | Chapter 14, section 3 |
| A lens's angle from `tan` of half of it; framing with `sin θ = r / d` | USD cameras; a camera that fits the scene | Chapter 14, sections 6 and 9 |
| A polygon's normal as the sum of cross products around its edges (Newell's method) | Flat normals for imported meshes | Chapter 14, section 12, building on Chapter 12, section 5 |
| Mip levels and `log2`; screen-space derivatives from 2x2 quads | Textures seen from far away; `fwidth` | Chapter 15, section 5 |
| Radiance and irradiance; Lambert's 1/π; Schlick's Fresnel; three BRDFs side by side (Lambert, normalized Blinn-Phong, and the GGX microfacet model with Smith's G), each as an equation and as code | Physically based materials, and a live toggle between the models | Chapter 15, section 9 |
| The tangent frame, made perpendicular with Gram-Schmidt | Normal maps | Chapter 15, section 10, from Chapter 12, section 5 |
| Solid angle; light units (lux, candela, watts); inverse-square falloff; color temperature | USD's lights | Chapter 16, section 2 |
| Fading between two values (`smoothstep`) | A spot light's edge; later, level of detail without popping | Chapter 16, section 5, with a worked number; again in Chapter 26, section 6 |
| Exposure in stops; tone curves | Bright scenes on a display | Chapter 16, section 6 |
| Orthographic projection; a box around a frustum | The sun's shadow camera | Chapter 17, sections 1–2 |
| Normalized device coordinates | Looking a point up in the shadow map | Chapter 17, section 6 |
| Depth-bias slope | Shadow acne | Chapter 17, section 9, in words with a worked number |
| Uniform and logarithmic splits | Shadow cascades | Chapter 17, section 11 |
| An enclosing sphere; snapping to texels | Shadows that hold still | Chapter 17, section 12 (the algebra is optional) |
| Samples and coverage | Anti-aliasing | Chapter 18, sections 1–2 |
| Coverage from `fwidth` | Soft cutout edges | Chapter 18, section 8, building on Chapter 15, section 5 |
| Hashing integers into uniform random numbers | Randomness on the GPU | Chapter 20, section 3; refined in Chapter 21, section 3 |
| Uniform random directions in a cone; stepping motion through time (Euler); exponential drag | Emitting and simulating particles | Chapter 21, section 3 |
| View space | Camera-facing billboards | Chapter 21, section 5 |
| Premultiplied alpha | Blending particles | Chapter 21, section 5 |
| Little's law | How many particles are alive | Chapter 21, section 7 |
| Depth back to view distance | Soft particles | Chapter 21, section 9 (exercise) |
| Cost as a product: pixels × overdraw × lights; bytes per pixel as bandwidth | Choosing forward or deferred | Chapter 22, section 1 |
| Octahedral encoding: a unit vector in two numbers | Normals in the G-buffer | Chapter 22, section 3 |
| Position from depth: the inverse view-projection and the divide by `w` | Lighting a pixel from the G-buffer | Chapter 22, section 5 |
| Planes through the eye from two projection entries; a sphere against a plane | Tiled light culling | Chapter 22, section 8, building on Chapter 12, section 10 |
| Positive floats ordered like their bit patterns | A min and max with integer atomics | Chapter 22, section 8 |
| A pixel's direction: un-projecting through the inverse of projection × rotation | The sky behind everything | Chapter 23, section 1 |
| Cube-map faces: the largest component picks the face; each face's right and down | Storing and sampling a sky | Chapter 23, section 2 |
| Latitude and longitude of a direction, both ways | Environment images, USD dome lights | Chapter 23, section 4 |
| A flat label on a sphere: dividing by the forward component | The test environment | Chapter 23, section 5 |
| A disk's solid angle; the radiance that delivers an irradiance, L = E / Ω | The sun's disk | Chapter 23, section 6, from Chapter 16, section 2 |
| Σ and ∫, the book's first: "add up the term for every piece", and the same for infinitely many infinitely small pieces; light on a surface as a cosine-weighted sum over the whole sky, stored as E / π | Ambient light from a sky | Chapter 24, section 1 |
| The solid angle of a cube texel, area / d³ | Adding up a sky stored in a cube | Chapter 24, section 2 |
| A weighted average over a lobe; splitting one sum into two (the split-sum approximation) | Reflections of a sky at every roughness | Chapter 24, sections 5–6 |
| A lobe's share within an angle; points placed by equal shares (importance sampling without random numbers) | The specular lookup table | Chapter 24, section 7 |
| Luminance, scene-referred soft thresholds, normalized reduction and convex reconstruction | Grading and a bloom pyramid whose gain does not depend on mip count | Optional Chapter 49, sections 1, 3 and 4 |
| Unprojected depth neighborhoods, geometric normals and spatial visibility weights | Ambient occlusion in scene units without final-color darkening | Optional Chapter 50, sections 2–5 |
| Optical depth and a slab integral; altitude profiles, ray/sphere distances, phase functions and explicit trilinear interpolation | Physical sky and finite-segment aerial perspective | Optional Chapter 51, sections 1–5, with its own worked primer before the cloud route |
| Jittered grids | Placing blades | Chapter 25, section 2 |
| A normal from two slopes | The ground's shading | Chapter 25, section 3 |
| Cubic Bézier curves and their tangents | A blade's shape and normal | Chapter 25, sections 6–7 |
| A pyramid of farthest depths; choosing its level with `log2` | Occlusion culling | Chapter 26, section 9 (optional) |
| Voronoi cells; gradient noise | Clumps; wind | Chapter 27, sections 1 and 2 |
| Pixels per metre from the projection | A minimum blade width | Chapter 27, section 4 |
| Light through a thin surface; a highlight in Blinn-Phong and in GGX | The grass's shading, with its own toggle | Chapter 27, section 7, from Chapter 15, section 9 |
| Density and extinction; mean free path; the number e and `exp`; Beer-Lambert's law, T = e^(−σd); optical depth | How much light gets through fog and cloud | Chapter 28, section 2 |
| A ray against a horizontal plane, t = (h − y) / d_y; a march as a sum of thin slices; one step's exact integral, S × (1 − e^(−σΔs)); jittering the start | Marching through the cloud layer | Chapter 28, section 3 |
| Phase functions; Henyey-Greenstein, one lobe and two | Which way a droplet scatters light; the silver lining | Chapter 28, section 6 |
| A 3D image's memory (n³; a 3D mip chain adds 1/7); Worley noise as the distance to the nearest Voronoi point, in 3D; noise that tiles; Perlin-Worley | Cloud shapes | Chapter 28, section 7, building on Chapter 27, sections 1–2 |
| Remapping a range onto [0, 1]; coverage as one subtraction; a height profile from two smoothsteps | Cloud density | Chapter 28, section 9 |
| A mip level from a footprint (log2 of metres per texel), without derivatives | Sampling far clouds in a compute shader | Chapter 28, section 9, building on Chapter 15, section 5 |
| Multiple scattering as a sum of octaves | White clouds with the sun behind you | Chapter 28, section 11 |
| A color's luminance as one number, 0.2126 R + 0.7152 G + 0.0722 B | How bright a white cloud should be | Chapter 28, section 11 |
| The exponential moving average: its noise (a variance), w / (2 − w), and its lag, (1 − w) / w | Hiding a march's noise; ghosting | Chapter 28, section 13 |
| Complex numbers as arrows; multiplying turns them | Waves with amplitude and phase | Chapter 29, section 1 |
| The inverse discrete Fourier transform; the FFT (butterflies, bit reversal) | Adding up every wave at once | Chapter 29, section 2 |
| Gaussian random numbers (Box-Muller, which uses `ln`, the inverse of `exp`); the Phillips spectrum | The sea's starting waves | Chapter 29, section 7 |
| The deep-water dispersion relation; differentiating a wave by multiplying by i k | Waves in motion, slopes, sharp crests | Chapter 29, section 8 |
| The Jacobian: how much a small square is squeezed; the determinant of Chapter 12, section 5 | Foam | Chapter 29, section 9 |
| Fresnel (Schlick) | Water's reflection | Chapter 29, section 10, from Chapter 15, section 9 |
| A repeat distance as a common multiple | Why one patch tiles; choosing patch sizes | Chapter 30, section 1 |
| Wavelength, wave number, and texels per wave; bands that do not overlap | Splitting waves between cascades | Chapter 30, section 2 |
| A spectrum over frequency turned into one over wave vectors (dω/dk, 1/k); the area under a curve in strips; Hs = 4√m0; steepness Hs/λp, which follows √α | JONSWAP, and "Energy x" | Chapter 30, section 5 |
| A function of direction normalized by summing it | Directional spreading | Chapter 30, section 6 |
| A narrow peak sampled by a coarse grid | A swell in a cascade | Chapter 30, section 7 |
| Exponential decay and its half-life, τ ln 2 | Foam that lingers | Chapter 30, section 8, from Chapter 21, section 3 and Chapter 28, section 2 |
| Normalizing a cos^p lobe around the reflection, (p+1)/2π | The sun's glint in the sun's units | Chapter 30, section 10, beside the Blinn-Phong factor in Chapter 15, section 9 |
| Premultiplied over: sky × (1 − a) + cloud | Clouds in the water | Chapter 30, section 10, from Chapter 21, section 5 |
| Fixed-point iteration: guess, see where it lands, correct by the miss | The water's height above a place | Chapter 31, section 3 |
| A speed as the change over one frame | How fast water comes at a rock | Chapter 31, section 5 |
| Rounding at random so the average comes out right | How many particles to ask for | Chapter 31, section 6 |
| Archimedes' principle, F = ρgV, a column at a time | Floating | Chapter 32, section 1 |
| Torque r × F; moment of inertia, m(a² + b²)/12 for a box; τ/I in a body's own axes; a rotation's transpose as its inverse | A rigid body | Chapter 32, section 2, building on Chapter 10, section 8 and Chapter 11, section 13 |
| The velocity of a point on a turning body, v + ω × r | Drag on the hull; the boat's spray | Chapter 32, section 2 |
| A spring's bob, √(k/m); a quaternion turned by an angular velocity, q + (h/2)(ω,0)q, normalized; substeps for a stiff spring | Moving the boat | Chapter 32, section 2, from Chapter 21, section 3 |
| A ray against a sphere: a quadratic in t | What each of the path tracer's rays hits | Chapter 33, section 3 |
| Probability, Monte Carlo integration, importance sampling, pdfs, Russian roulette | The path tracer | Chapter 33, sections 0 and 4 (importance sampling first met, without randomness, in Chapter 24, section 7) |
| The area of a disc, πR²: ground grows with the square of the distance; a thing of size s at distance d spans about s/d radians | Why the far view needs level of detail | Chapter 35, Where this is going |
| Float spacing, 2^(k−23) between 2^k and 2^(k+1) | Positions far from the origin; depth | Chapter 35, section 4; again in Chapter 35, section 5 |
| Depth's change per metre, n/d²; the smallest step, d²·2⁻²⁴/n stored the usual way and d·2⁻²³ stored reversed | Seeing far without z-fighting | Chapter 35, section 5 |
| Counting the steps between two floats from their bit patterns | The steps readout | Chapter 35, section 6, from Chapter 22, section 8 |
| Doubling: twelve rings of one grid, each twice the last, reach 2¹¹ times as far for twelve times the cost | Clipmap rings | Chapter 36, section 2 |
| Cells per wavelength (two to draw a wave, four to keep its shape); the largest cell at distance d, d/(N/4 − 1); smoothstep as a fade | Detail by distance | Chapter 36, section 3 |
| A bilinear sample worked by hand | The heightmap's height on the CPU | Chapter 36, section 9 |
| Where a world point lies on a map: (xz + MAP_ORIGIN) over the map's side, plus a half | Which texel lies under a point | Chapter 36, section 9 |
| A mip level as an average, and a blend between two levels | Standing objects on the ground the rings draw | Chapter 37, section 4, from Chapter 36, section 9 |
| An object's height on screen in pixels; a band of hysteresis around each threshold | Choosing an object's level | Chapter 37, section 5, from 35 |
| Value noise | Where the forests stand | Chapter 37, section 6 |
| A remainder that is never negative; the smallest move worth making, in pixels | A pool of near trees that wraps round | Chapter 37, section 7 |
| Weights that add up to 1, and why bilinear filtering and mip levels keep them so | A material map that can be filtered | Chapter 38, section 1 |
| An octave faded by the ground one pixel covers, from the world position's screen derivatives | The far colour's lighter and darker patches | Chapter 38, section 3, from Chapter 36, section 3 and Chapter 15, section 5 |
| A slope s as a normal's y, 1/√(1 + s²) | Rock wherever a pixel is steep | Chapter 38, section 3 |
| A texel's size in metres against a pixel's | Tiling a photograph at its real size | Chapter 38, section 6 |
| A gain in linear light that moves an image's mean and keeps its contrast | Tinting a photograph to the island's colour | Chapter 38, section 6 |
| A tangent made from a world axis, Gram-Schmidt | Normal maps on ground with no tangents | Chapter 38, section 7, from Chapter 15, section 10 |
| A stretch between two percentiles; blending by height | Borders of clumps and stones | Chapter 38, section 8 |
| Three projections weighted by the normal's components to the fourth power; a projection from above stretched by 1/cos | Rock on cliffs | Chapter 38, section 9 |
| A ring of points round a turning axis; a frame turned by Rodrigues' rotation | Branches | Chapter 39, section 1, from 10 |
| A normal pointing away from the crown's middle; keeping the leaves' area with fewer cards | Leaf cards and their levels | Chapter 39, section 2 |
| A texel's size against a card's | Why far trees cast their solid stand-ins | Chapter 39, section 4 |
| The share of texels above a cutoff, a quantile, and the scale that restores it | Leaves that do not thin with distance | Chapter 39, section 6, from Chapter 18, section 8 |
| A count added per layer, read through the sRGB curve | The overdraw view | Chapter 39, section 7 |
| An edge as 4w(1 − w); a slope from a central difference; chances from weights | Where the understory grows | Chapter 39, section 8 |
| The cells a circle holds | Sizing the understory's grid | Chapter 39, section 9 |
| A turn about +Y written out | Planting each plant | Chapter 39, section 10 |
| A budget from measured times | What the understory may cost | Chapter 39, section 11 |
| A position kept as the sum of every frame's move, not velocity times time; the chord between two unit directions, 2 sin(Δθ/2), and the jump it causes, 2·v·t·sin(Δθ/2) | Gusts that do not jump when the wind turns | Chapter 42, section 2, from Chapter 27, section 2 |
| The difference of two angles brought into (−180, 180], the short way round; a turn of at most rate × dt a frame that lands exactly on its target | A wind that turns at a set rate | Chapter 42, section 2 |
| One shared HLL face flux, per-side hydrostatic pressure corrections, a two-stage update and a numerical CFL bound | Moving water without losing volume or disturbing a still lake | Chapter 43, section 0 |

### Color, across the whole tutorial

Color is decided in one chapter and paid for in four others. Chapter 3, section 2 shows what the sRGB curve does to numbers; Chapter 8, section 4 has
the plan and its full table. *Linear* is where lighting math is correct, and
*sRGB-encoded* is what the display expects and 8-bit images store: everything
the scene computes stays linear, in an `R16G16B16A16_SFLOAT` target, and the
composite pass encodes to sRGB **exactly once**, at the end.

**Who does the encode, chapter by chapter:**

| Chapter | Swapchain | Encoder | What you see |
| --- | --- | --- | --- |
| 3–6 | `B8G8R8A8_SRGB` | The hardware, on every write | Correct. The clear color and triangle are linear values encoded once. |
| 7 | `B8G8R8A8_SRGB` | The hardware — including on ImGui's bytes, which are already sRGB | ImGui looks pale: its colors are encoded a second time. Expected, and left alone for one chapter. |
| 8 | `B8G8R8A8_UNORM` | The composite pass | Scene correct; ImGui correct, because the UNORM image stores its bytes untouched. The triangle looks as it did in Chapter 6 — the check that the switch worked. |
| 16 | `B8G8R8A8_UNORM` | The composite pass, now with exposure and a tone curve | Physical light values — and later the path tracer's HDR output — compress into range instead of clipping. Defaults reproduce Chapter 8 exactly. |

**Why not the alternatives.** Keeping `_SRGB` and correcting ImGui's style
colors makes every color picked from a reference wrong. A UNORM swapchain with
no composite pass means every final shader must remember to encode. A
mutable-format swapchain with both an sRGB and a UNORM view works, but needs an
extension to solve what the offscreen target already solves.

**The three rules that follow from it** (Chapter 8, section 4):

1. Everything entering the scene arrives linear: color textures are `_SRGB`,
   data textures `UNORM` or `SFLOAT`. An `_SRGB` image's alpha stays linear,
   so a number can travel there (Chapter 38 keeps a photograph's height in it).
2. What ImGui shows stays in sRGB bytes: images shown only through
   `ImGui::Image` are `UNORM`, and `ColorEdit` colors are converted before the
   scene uses them.
3. Only the composite pass encodes. On an `_SRGB` swapchain its `encodeSrgb`
   specialization constant turns that encode off.

### Cameras, geometry, and scenes, across the tutorial

Like color, these are decided once and then used by every chapter from 10 on.
Each row names the chapter that teaches it; this table is only the summary.

**Conventions.**

| Thing | Convention | Taught in |
| --- | --- | --- |
| World space | Right-handed, +Y up, one unit is one metre | 10. A USD stage that is Z-up or in centimetres is converted once, at import (14). |
| View space | The camera sits at the origin looking down −Z, +Y up — what `glm::lookAt` builds | 10 |
| Clip space | Vulkan's: +Y points down, depth runs `[0, 1]`. The projection matrix negates `[1][1]`, and `GLM_FORCE_DEPTH_ZERO_TO_ONE` (premake) gives `[0, 1]`. Nothing else flips Y — not the viewport, not the shaders | 10 (6 previewed it) |
| Depth | `D32_SFLOAT`, cleared to `1.0`, compared with `LESS`. Reverse-Z is explained as an aside (10) and used inside one demo only, Chapter 35's `Horizon`, which teaches it as sky first, depth cleared to 0 mid-pass, then `GREATER`; from Chapter 41 the pass begins cleared to 0, the sky compares `GREATER_OR_EQUAL`, and there is no mid-pass clear. Shadow maps stay conventional. The engine and every other demo keep this row | 10, 35, 41 |
| Winding | Meshes are counter-clockwise seen from the front, as in USD, glTF, and OpenGL. The projection's Y flip keeps the picture upright, so they are counter-clockwise on screen too: `frontFace = COUNTER_CLOCKWISE`, `cullMode = BACK`. The triangle from Chapter 6 stays `CLOCKWISE`, because its positions are written straight into Vulkan's Y-down clip space with no projection | 11 |
| Indices | `uint32_t` | 11 |
| The sun's direction | The way sunlight *travels*, from the sun toward the scene (`sunDirection`); code that needs the opposite names it `toSun` | 11, 16 |
| The wind | Where it *blows toward*, in degrees turning from −Z toward +X, which is the unit vector (sin a, −cos a) in world x and z; its mean speed in metres per second; gust strength from 0 to 1; gust size in metres. A demo owns one `WorldWind` and writes it into `FrameData` once a frame; all zero is calm. The owner refuses a gust size under `WorldWind::MIN_GUST_SIZE` (0.5 m), and every reader treats a smaller one, such as calm's 0, as no gusts and never divides by it. The gust offset is the sum of every frame's travel, and the direction turns toward the one it is given at a turn rate, the short way round; the owner refuses an angle past a full turn either way. The sea's spectrum and the clouds keep winds of their own | 27 (section 2), 42 (sections 1 and 2) |
| Plant space | A plant file stands at the origin, y = 0 is the ground, its stem leaves along +Y; its height is LOD0's top; every card's `uv.y` is 1 at its base; leaf normals are crown normals; subsets come in the same order at every level, `<Plant>Bark` first where it has one (the fern has none), then `<Plant>Leaf`, `<Plant>Head` or `<Plant>Far` | 39 (section 2) |

**Where the code lives.**

| Module | Namespace | Holds |
| --- | --- | --- |
| `Source/PillowFort/Scene/` | `pf::scene` | CPU-side and Vulkan-free: `Transform`, `Camera`, the fly and orbit controllers (10); `Vertex` and `MeshData` (11); `Scene` and its nodes (12); materials (15) and lights (16) as plain data |
| `Source/PillowFort/VulkanGraphics/` | `pf::vulkan_graphics` | The GPU side of the same things: the per-frame buffer (10), mesh upload (11), material descriptor sets (15); and the CPU owners of what that buffer carries for the whole frame, such as the world wind (42) |
| `Source/PillowFort/UsdImport/` | `pf::usd_import` | The only code that includes a TinyUSDZ header (13, 14; `ImportGrayImage16`, a 16-bit grayscale PNG, Chapter 36, section 8; `ImportRgbaImage8`, an 8- or 16-bit PNG as four 8-bit channels, Chapter 38, section 2) |
| `Source/PillowFort/Demos/<Name>/`, `Shaders/<Name>/` | per demo | Anything one demo needs and the next would not |

**Names.** Member functions are PascalCase (`Camera::Projection`) in
`VulkanInstance` (2) and in every class from Chapter 9 on (`Demo`,
`SceneRenderer`, `Sky`, ...): the engine's house style. The other classes of
Chapters 2–7 — `InitializationResult` and `GlfwWindow` (2),
`VulkanSwapchain` (3), `VulkanRenderer` (4), and `ImGuiDebugPanels` (7) —
keep lowercase names, like the older `Log`, including what later chapters add
to them (`renderer.setSampleCount`, 18), until they are converted as a whole. Free functions are camelCase (`createBuffer`,
`uploadMesh`, `computeBounds`), except UsdImport's four entry points,
`ImportUsdFile`, `LogUsdPrimTree`, `ImportGrayImage16` and `ImportRgbaImage8`.

**The vertex**, fixed in Chapter 11 so that every later chapter can rely on it:

```cpp
// Source/PillowFort/Scene/MeshData.h
struct Vertex
{
    glm::vec3 position;   // offset  0
    glm::vec3 normal;     // offset 12
    glm::vec2 uv;         // offset 24
    glm::vec4 tangent;    // offset 32: xyz tangent, w = bitangent sign (Chapter 15)
};
static_assert(sizeof(Vertex) == 48);
```

The tangent is there from the start, unused until Chapter 15, so that normal
mapping does not change the vertex format, every pipeline's vertex input, and
the importer at once.

**Descriptor sets.** Chapter 8, section 6 introduced the idea of grouping by how
often things change. From Chapter 10 on it is concrete:

| Set | Bound | Contents | From |
| --- | --- | --- | --- |
| 0 | once per frame | everything every draw in the frame shares; its bindings are listed below | 10, grown by 11, 15, 16, 17, 19, 22, 24, Renderer convergence (after 39), 51 and 42 |
| 1 | per material | binding 0: material parameters; bindings 1 and up: its textures (in Horizon, set 1 is the island: see Horizon's own layouts) | 15 |
| the sky (23) | its own layout | set 0, binding 0: the sky cube (`samplerCube`); push constants: `SkyDrawParameters`. Draw it last in a scope, or rebind your sets after it (Horizon, Chapter 35, section 7, draws it first under reversed depth) | 23 |
| push constants | per draw | the model matrix (and later a material or instance index) | 11 |
| set 0, binding 2 | per instance | transforms indexed by `gl_InstanceIndex`, one buffer per frame in flight, replace the per-draw push constant. Compute-generated instances (21 onward) use their own buffers and layouts | 19 |

**Horizon's own layouts (35–48).** These are layouts only that demo uses.
In each, set 0 is `SceneRenderer`'s, as listed above.

| Set | Bound | Contents | From |
| --- | --- | --- | --- |
| the Horizon flat pipeline (35) | its own layout | set 0 from `SceneRenderer` (bindings 0 and 2; from 37 also 3, 4, 10 and 11); push constants: `FlatDraw`, 16 bytes, 48 from 37 | 35, 37 |
| the terrain (36, 38) | its own layout | set 0 from `SceneRenderer` (binding 0; bindings 3 and 4, the shadows, from 37; and 10 and 11 for the sky's light); set 1, the island (Chapter 38, section 2): binding 0 the heightmap (`sampler2D`, `R16_UNORM`, every mip level), 1 the material map (`sampler2DArray`, two layers, `R8G8B8A8_UNORM`), 2 the photographs' colours with their heights in alpha (`sampler2DArray`, six layers, `R8G8B8A8_SRGB`), 3 their normals (`sampler2DArray`, six layers, `R8G8B8A8_UNORM`), every binding visible to the vertex, fragment and compute stages; the coast adds bindings 4-9, the coastal bed's nodes (4) and its wet history (5), the coastal sea's three cascade maps (6-8) and their parameters (9, a uniform buffer); push constants: `TerrainDraw`, 64 bytes; no vertex buffer | 36, 38, 41, 43 |
| the Horizon leaf pipelines (39) | its own layout | set 0 from `SceneRenderer`, as the flat pipeline's; set 1, the island (Chapter 38, section 2), in the layout and never read by a leaf shader; set 2, the run's material: the engine's own set, from `SceneRenderer::MaterialSet`, bound at 2; push constants: `FlatDraw` then `LeafDraw`, 96 bytes | 39 |
| the understory's generate pass (39) | its own layout | set 0 in the layout, unbound; set 1, the island; set 2, its parameters (uniform), instances and commands (storage); push constants: `TerrainDraw`, 64 bytes; compute only | 39 |

Set 0's bindings, and the chapter that adds each:

- **binding 0:** the frame uniform buffer, `FrameData` — `view`, `projection`,
  `viewProjection`, `cameraPosition`, and time (10); the sun and the ambient
  light (11); `brdf` (15); `inverseViewProjection` (22); `ambientMode` (24);
  `haze` and `hazeSky`
  ([Renderer convergence](Tutorial/RendererConvergence.md#shared-distance-haze),
  after 39), then the opt-in atmosphere parameters (51), then the world
  wind, `windDirection` and `windGust` (42). The appendix shows it whole.
- **binding 1:** the light storage buffer (16).
- **binding 2:** the per-instance storage buffer (19).
- **bindings 3 and 4:** the shadow cascades' uniform buffer and the cascaded
  shadow map, a `sampler2DArrayShadow` (17).
- **bindings 10-12:** the sky's light — the diffuse cube and the specular cube
  (`samplerCube`), and the split-sum table (`sampler2D`) (24).
- **bindings 13-15:** the atmosphere's solar transmittance, aerial scattered
  radiance and aerial optical depth (51), borrowed from `Sky`'s atmosphere
  owner. Aerial radiance uses filtered RGBA16F; optical depth uses RGBA32F
  with eight explicit texel fetches and seven vector mixes. Valid neutral
  images are supplied even when physical mode is off.
- **bindings 5-9** stay free: Chapter 22's lighting set reuses set 0's numbers
  and puts its own images there.

Chapter 50 additionally uses binding 20 in `DeferredShading`'s own lighting
set for screen AO. That is a different layout from the shared scene frame
set; the number does not add AO to every forward pipeline.

The frame block's C++ and GLSL twins live in `Shaders/Include/SharedShaderTypes.h`,
the shared header Chapter 8, section 8 sets up. Compute passes (20 onward) use
their own layouts; nothing above constrains them.

**Who owns what in a frame.** The appendix draws all of it; these are the rules.

- **The engine owns the window-sized images.** `VulkanRenderer` owns the scene
  color target (8), the single-sample scene depth (10, created with `SAMPLED`
  usage so later chapters can read it), and from Chapter 18 the multisampled
  color and depth that resolve into those two. It creates and rebuilds them.
- **When only the extent changes**, it calls the demo's `Resize` with the new
  size and handles, so the demo can rebuild its own window-sized images and
  rewrite descriptors.
- **When a format or the sample count changes** (Chapter 18's picker), it
  re-runs the demo: `Teardown`, then `Setup` with the new formats, exactly like
  switching demos — so pipelines are only ever built in `Setup`. That works
  because `Teardown` releases GPU objects only: a demo's CPU-side state —
  slider values, an imported `pf::scene::Scene`, inspector edits, the camera —
  lives in the demo object and survives.
- **The scene part of the frame belongs to the demo**, exactly as Chapter 8, section 4's contract says: the demo receives the scene target and hands it
  back in `SHADER_READ_ONLY_OPTIMAL` with its writes visible to the fragment
  shader, and everything in between is its business — compute dispatches,
  shadow passes, a rasterized pass, more drawing after it. A rasterizing demo
  opens its pass through an engine helper that sets up the color, depth, and
  (from Chapter 18) multisample-resolve attachments, so the resolve logic
  exists once; a compute demo such as the path tracer never calls it. The
  demo's `Record` is told which frame in flight it is recording, and runs after
  that slot's fence has been waited on.
- **Drawing a `pf::scene::Scene` is a reusable class** in `VulkanGraphics` — it
  owns set 0's layout and per-frame buffers, the mesh pipelines, and the
  recording of a draw list — introduced in Chapters 10–12 and grown by 15–19 and 22
  (materials, lights, shadows, sample count, instancing, and the deferred path,
  whose G-buffer it rebuilds when the demo's `Resize` passes the new targets
  on). A demo that shows a scene owns one. So does a demo with its own
  pipelines that also draws scene objects, and it binds the renderer's set 0
  into those pipelines: the grass draws its stones and shadows through it, the
  sea its rock and boat with the shared materials, lighting and shadows, and
  Horizon's plates, terrain, plants and impostors all share that set 0.
  Cubes, the particles and the ocean need only the camera, so they own
  Chapter 10's camera-only `FrameBindings` instead (the appendix's "Patterns
  already converged").

**The scene graph**, Chapter 12, in four sentences. `Scene` owns a vector of
nodes and arrays of meshes, cameras, materials, and lights; nodes refer to
their parent, children, and components by index, never by pointer. World
transforms are recomputed top-down once per frame, only below nodes whose local
transform changed. The renderer never walks the tree: each frame the scene
produces a flat list of draws — mesh, material, world matrix — and that list is
all the GPU side sees. The active camera is just a node index, and a controller
moves a camera by writing that node's local transform.

Chapter 10 comes before the scene graph, so its camera owns its own `Transform`.
Chapter 12 moves that transform onto a node, and says so in a **Jump** box.

### Dependencies the SDK already gives you

ROADMAP's Guardrail 5 — add a dependency only when it removes work that is not
part of the goal — decides these. What tips the balance is that **all three
ship with the Vulkan SDK**, at `%VULKAN_SDK%\Include\{glm,vma,Volk}`, as
optional components of its Windows installer: GLM and VMA are needed here, so
select them when you install (Chapter 1, section 1 says how to check).
Adopting one is then an `includedirs` line, not a submodule, a build-system
change, or a license question.

| Dependency | Recommendation | Reasoning |
| --- | --- | --- |
| **GLM** | Already in (the `Camera` module uses it) | `GLM_FORCE_DEPTH_ZERO_TO_ONE` encodes Vulkan's `[0, 1]` depth convention, which you would otherwise rediscover painfully. Define it once in `premake5.lua` (Chapter 1's workspace does), never per file — Chapter 6, section 2 says why. It does not handle the Y flip; Chapter 10, section 2 does. Current GLM uses radians unconditionally, so `GLM_FORCE_RADIANS` is no longer needed. |
| **VMA** | Read a hand-rolled allocation once, then switch, both in Chapter 8 | Seeing memory allocated by hand exactly once is genuinely instructive: heaps, memory types, alignment, and mapping. Doing it for the dozens of buffers and textures a scene needs is not, because at that point you are writing a suballocator, which is not a Vulkan learning goal. |
| **Volk** | Skip; reconsider for Chapter 33 route C | You link `vulkan-1.lib` directly and target one platform. Volk buys loader-bypass dispatch and extension-function loading you do not need; route B loads its five ray tracing functions by hand, and Chapter 43's shoreline its two conditional-rendering ones. |

One place the roadmap's defaults are worth bending once the demos start:
**FIFO present mode** is right for the foundation and mildly annoying once you
have ImGui sliders, because it adds latency to every drag. Chapter 3 makes the
present mode a setting — from the command line at startup, from a Chapter 7
picker at runtime — because which modes exist depends on the GPU. The same goes
for the GPU itself on a machine with two (Chapter 2, section 5).

### Repository conventions this tutorial follows

Per [ROADMAP.md](../ROADMAP.md):

```text
VulkanGraphics
  path:      Source/PillowFort/VulkanGraphics
  namespace: pf::vulkan_graphics
  include:   PillowFort/VulkanGraphics/VulkanInstance.h
```

- Backend-specific types carry their backend: `VulkanInstance` (which also
  owns the device here; ROADMAP's example name is `VulkanDevice`),
  `GlfwWindow`, `ImGuiDebugPanels`.
- Constructors do not perform fallible GPU work. Initialization returns a
  descriptive result type.
- Assertions are for programmer mistakes. Unsupported hardware and missing files
  are reported, not asserted.
- Exceptions do not cross module boundaries.

Code in this tutorial follows that style: initialization functions return a
result, and each chapter names its module up front. Where a snippet is not a
whole function, the section says which function it belongs to — Chapter 2's
"What you are actually writing" is the pattern the rest follow.

---

## Appendix: The engine you built

A reader's map for the end of the book, or for any time you lose track of where
something lives: what owns what, what one 3D frame does in order, the frame
block whole, and one list of everything the chapters name and do not build.
Nothing here is new; each line names the chapter that built it. A line marked
*convergence* names [Renderer convergence](Tutorial/RendererConvergence.md),
the page after Chapter 39 where code the demos had repeated became shared
before Chapter 40: one owner for mesh geometry, an explicit depth convention,
shadow-cascade visibility separate from the camera's, and, in its optional
step 4, one FFT owner, `OceanFft`, for the ocean and the sea.

### What owns what

`SandboxGame`'s `main` constructs everything, in order, and owns all of it. No
object finds another through a global; each is handed what it uses.

```text
main (SandboxGame/Main.cpp)
├── GlfwWindow                          02   the window and its event queue
├── VulkanRenderer                      04   the frame
│   ├── VulkanInstance                  02   instance, debug messenger, surface, device, queue
│   ├── VulkanSwapchain                 03   images, views, a renderFinished semaphore per image
│   ├── FrameResources × 2              04   per frame in flight: command pool and buffer, fence, imageAvailable
│   ├── pipeline cache                  06   saved to disk at shutdown
│   ├── VulkanContext                   08   borrowed handles, the VMA allocator, an immediate-submit pool
│   ├── scene color, RGBA16F            08 ┐
│   ├── scene depth, D32, sampled       10 ├ window-sized, rebuilt on resize, lent to the demo as SceneTargets
│   ├── multisampled color and depth    18 ┘
│   ├── composite pass                  08   samples the scene color into the swapchain image
│   ├── ToneMappingSettings             16   exposure and curve, read by the composite pass; main draws the panel
│   ├── Bloom and grading               49   resolved HDR pyramid before the composite, neutral-default RGB gain/saturation
│   ├── final-output readback           49   requested copy of actual pre-UI swapchain pixels
│   ├── SkySettings (+ CloudSettings)   23   handed to the demo in RecordContext; main draws the panel (28 adds the clouds')
│   ├── ImGuiDebugPanels                07   the backend, the frame panel, the present-mode, demo, and MSAA pickers
│   └── the active Demo, borrowed       09
└── every Demo, one push_back each      09   switched by the picker; only the active one is set up
```

Each demo is a folder under `Demos/` and owns its GPU objects from `Setup` to
`Teardown`. What each one owns, besides its own pipelines:

```text
Triangle, Gradient    09      a pipeline and its push constants (the triangle's moved here from VulkanRenderer)
Cubes                 10      FrameBindings (camera-only set 0), Sky
Meshes                11      SceneRenderer, Sky
Scene graph           12      SceneRenderer, Sky, a pf::scene::Scene and its panels
USD viewer            14-24   SceneRenderer, Sky, a Scene imported by UsdImport, light glows (22), its own timestamps (22)
Life                  20      two cell images, ping-ponged; a statistics buffer and its readback
Particles             21      FrameBindings, Sky, the particle pool and lists, its own timestamps; optional sampled-depth soft intersections
Grass                 25-27   SceneRenderer, a Scene of stone and ball nodes, Sky, blade and counter buffers, a depth pyramid (26), GpuTimestamps (26),
                              a WorldWind (42)
Ocean                 29      FrameBindings, FFT images, a sky gradient of its own
Sea                   30-32   SceneRenderer (materials, lighting and shadows), Sky, three FFT cascades, GpuTimestamps,
                              SeaObjects: retained imported Scene assets, GPU boat pose, the probe set, spray requests, SprayParticles
Path tracer           33      the accumulation image; route B's MeshScene: buffers, BLAS, TLAS
Horizon               35-43/48 SceneRenderer (set 0, the batches of its plates and props, shadows), Sky, a flat pipeline of its own, reversed depth inside this one demo;
                              Terrain (36, 38): clipmap rings over an R16 heightmap with its mips, and GroundMaterials (38): the material map and six ground photographs, in the island's set 1;
                              Props (37): a scene graph of its own, LOD0-LOD2 by height on screen, a pool of near trees; GpuTimestamps;
                              Plants (39): the leaf pipelines (a run's material at set 2, instance-rate attributes for the understory); Understory, a compute pass that plants and counts (section 9), drawn indirectly (section 10), borrowing shared mesh geometry;
                              Impostors (40): cached multi-view surface data, persistent chunked forest cells, shared near/far ownership, independent geometry shadow proxies;
                              WorldWind (42): the demo's one wind, which the coast's grass reads through FrameData
```

The engine classes those demos compose, in `VulkanGraphics`:

```text
FrameBindings           10      camera-only set 0 and its per-frame uniform buffers
FrameData.h             10, 22  CPU camera/matrix preparation, with the projection supplied explicitly by each demo; applyWorldWind (42)
SceneRenderer           11-24   rich set 0, and a Scene's draw list, drawn
├── set 0               10      FrameData (10), lights (16), instances (19), shadow data and map (17), sky light (24); from 39, FrameSetBindings(), the bindings its layout was made from
├── geometry            11, 19  every mesh in one vertex buffer and one index buffer
├── materials           15, 39  set 1 per material, textures, sixteen samplers, a white texture; from 39, MaterialSetLayout() and MaterialSet(material), read-only, so a demo's pipeline binds a material's set at a number of its own, and MaterialSetBindings(), the bindings its layout was made from. Horizon counts the samplers its leaf pipelines ask of one stage from FrameSetBindings(), MaterialSetBindings() and Terrain's IslandSetBindings()
├── mesh pipelines      11, 15  one per shading mode, opaque and cutout; a sample count from 18
├── batches             19      instancing and multi-draw indirect
├── ShadowMaps          17      the sun's cascades in one layered depth image
└── DeferredShading     22, 50  the G-buffer and tiled lighting; opt-in spatial AO before diffuse ambient evaluation

Sky                     23      owned by each demo that shows one: Update before the scene pass, Draw inside it
├── the sky cube        23      baked by compute only when its inputs change
├── ImageBasedLighting  24      diffuse cube, specular cube, split-sum table: set 0's bindings 10-12
├── Atmosphere          51      physical sky/transport LUTs, with separate lighting and observer update domains
└── Clouds              28      noise images, a weather map, a march into a cloud cube every frame

GpuTimestamps           24      used by ImageBasedLighting, Clouds, grass, sea, AO, atmosphere and renderer bloom boundaries
WorldWind               42      CPU only: one demo's wind, its settings checked, its state written into FrameData once a frame
OceanFft                convergence  step 4, optional: one inverse-FFT resource owner and stage scheduler for Ocean's field and Sea's independent cascades

VulkanResources         08, 20  free functions: buffers and uploads (08); createStorageImage and
                                createDescriptorSets (20), which every demo from 20 on uses
VulkanBarriers          04-20   transitionImage (04), memoryBarrier (19), computeToComputeBarrier (20)
```

Beside them, `pf::scene` holds everything Vulkan never sees — `Transform`,
`Camera` and its controllers (10), `MeshData` and the mesh generators (11),
`Scene` (12), materials (15), and lights (16) — and `pf::usd_import` fills a
`Scene` from a USD file (13–14).

### One 3D frame, in order

From the top of the main loop to the present, with every pass the late
chapters add. No demo runs all of it — the USD viewer, the grass, and the sea
each run a different subset — but every demo keeps this order, except that
demos order steps 7–9 differently. Those steps are free to move only where one
does not read another: Chapter 41's coast draws its generated blades into the
shadow cascades, so its compute (7) must come before its shadows (8). One demo
reorders step 10 itself: Horizon draws its sky first, under reversed depth.
Chapter 35 (sections 6 and 7) does that with a clear of depth to 0 mid-pass;
from Chapter 41 the pass begins cleared to 0 and the sky compares
`GREATER_OR_EQUAL`. The list below stops at Chapter 32's passes; Horizon adds
more to steps 7 and 11: the understory's planting (39), the coastal grass
(41) and the shoreline solver (43) in compute, and, at the coast, a second
scope after the opaque scene, in which the water reads a copy of the opaque
color and depth (Chapter 43, section 6).

The optional refinements enter these boundaries without changing their
ownership: Chapter 51 updates atmosphere LUTs before sky/IBL use and applies
finite transport at each supported surface's haze hook. Chapter 50's opt-in
single-sample deferred route inserts AO between G-buffer generation and
diffuse ambient evaluation; its scene payload is emission/material AO until
lighting consumes it. Chapter 49 inserts bloom after scene handback and grades
the final composite. A requested final-output capture copies that actual
composite before the UI, then resumes the UI attachment with `LOAD`.

```text
On the CPU, in main (07, 09)
 1. poll events; begin the ImGui frame; draw the engine's panels and pickers
 2. switch demo or sample count, if asked (09, 18): Deactivate, Teardown, Setup
 3. demo.Update: events, the camera, the demo's panels

VulkanRenderer::drawFrame (04)
 4. wait for this slot's fence; acquire a swapchain image; reset the slot's command pool

demo.Record — outside any rendering scope first (09)
 5. read back what this slot copied and timed last time; reset its queries         Chapter 20, section 9, Chapter 21, section 8
 6. write this slot's FrameData, lights, and instances into mapped buffers        10, 16, 19
 7. compute that feeds the frame: particles emit and simulate (21), blades generated and culled (26),
    FFTs, foam, probes, spray requests, and the boat (29-32)
 8. shadows: one depth pass per cascade (17)
 9. Sky::Update: bake the cube if its inputs changed (23), filter its light if it was baked (24),
    march the clouds (28)
10. the opaque scene, one of two ways:
      forward   beginScenePass → mesh draws → Sky::Draw, the sky then the clouds → endScenePass,
                which resolves MSAA (18)
      deferred  G-buffer pass → tiled lighting in compute → Sky::DrawInOwnPass (22, 23; 1x only)
11. second scopes over the finished scene: particles (21), light glows (22), spray (31)
12. hand the scene target back, written and in SHADER_READ_ONLY_OPTIMAL           Chapter 8, section 4, 09
13. the grass only: reduce this frame's depth into the pyramid next frame tests   Chapter 26, section 9

VulkanRenderer::recordFrame, the engine's part (05, 08)
    optional bloom on the resolved HDR scene                                     49
14. the swapchain image: UNDEFINED → COLOR_ATTACHMENT_OPTIMAL, after the acquire
15. composite: bloom combine → exposure/gain/saturation → tone curve → encode     08, 16, 49
16. ImGui on top                                                                   07
17. → PRESENT_SRC_KHR

drawFrame again
18. after recording succeeds, reset the slot's fence and submit: wait on imageAvailable at
    COLOR_ATTACHMENT_OUTPUT; signal the image's renderFinished and the slot's fence
19. present; recreate the swapchain if it is out of date or the window was resized   Chapter 3, section 7
```

Chapters 4–10 establish `InitializationResult` returns for frame recording
and required mapped-buffer writes. Later chapters extend that same contract,
because an upload can fail after recording has begun. A
failed frame, light, instance, shadow, grass or understory upload reaches
`drawFrame` before anything is submitted, and the slot's fence is reset only
when a submission will follow (step 18), so a failed frame never leaves the
fence waiting for work that was never sent. The
[fallible-frame checkpoint](Tutorial/RendererConvergence.md#ch39-convergence-fallible-frame)
audits this failure path through the forest's expanded writers and complete
fallbacks. It does not give every Vulkan return value in the
program a recovery policy.

### `FrameData`, whole

Set 0, binding 0, written by every 3D demo once per frame. It grew in several
chapters under one rule — append at the end, never move a field — so no
chapter shows its final form. This is it, from
`Shaders/Include/SharedShaderTypes.h`:

```cpp
/* Chapter 10: everything that is the same for every draw in a frame. Set 0,
   binding 0, std140. Append-only: a later chapter adds fields at the END and
   updates the asserts, so no shader written earlier reads the wrong offset. */
struct FrameData
{
    mat4  view;             /*   0  world -> view */
    mat4  projection;       /*  64  view -> clip: Vulkan's, Y down, depth [0, 1] */
    mat4  viewProjection;   /* 128  projection * view, multiplied once here, not per vertex */
    vec4  cameraPosition;   /* 192  xyz world-space eye; w = 1 */
    float time;             /* 208  seconds since startup */
    float deltaTime;        /* 212  seconds since the previous frame */
    float padding0;         /* 216  keeps the size a multiple of 16 */
    float padding1;         /* 220 */
    /* Chapter 11: one directional light and an ambient term. */
    vec4  sunDirection;     /* 224  xyz: the unit direction sunlight TRAVELS, sun to scene; w unused */
    vec4  sunColor;         /* 240  rgb linear: what a white surface facing the sun reflects; w unused */
    vec4  ambientColor;     /* 256  rgb linear: light from everywhere else; w unused */
    /* Chapter 15: which BRDF shades every surface, the same for every pixel. */
    uint  brdf;             /* 272  BRDF_*; 0 is GGX */
    uint  padding2;         /* 276  keeps the size a multiple of 16 */
    uint  padding3;         /* 280 */
    uint  padding4;         /* 284 */
    /* Chapter 22: clip space back to world space, for a pass that knows only a pixel and its depth. */
    mat4  inverseViewProjection;   /* 288  inverse(viewProjection) */
    /* Chapter 24: the ambient light's source, the same for every pixel. */
    uint  ambientMode;      /* 352  AMBIENT_*; 0 is Chapter 16's constant */
    uint  padding5;         /* 356  keeps the size a multiple of 16 */
    uint  padding6;         /* 360 */
    uint  padding7;         /* 364 */
    /* Renderer convergence: shared distance haze, off for every earlier caller by default. */
    vec4  haze;             /* 368  fallback linear RGB; w metres, <= 0 disables haze */
    uint  hazeSky;          /* 384  nonzero: use the sky environment behind the surface */
    uint  padding8;         /* 388 */
    uint  padding9;         /* 392 */
    uint  padding10;        /* 396 */
    vec4  atmosphere;       /* 400: enabled, solar exposure, aerial max metres, observer altitude metres */
    /* Chapter 42: the world wind, written once a frame by the demo's one owner. All zero is calm. */
    vec4  windDirection;    /* 416  xy: unit vector the wind blows along, world xz; zw: gust offset, metres */
    vec4  windGust;         /* 432  x strength 0..1, y gust size metres, z mean speed m/s; w unused */
};

#ifdef __cplusplus
    static_assert(sizeof(FrameData) == 448, "FrameData layout drifted.");
    static_assert(offsetof(FrameData, cameraPosition) == 192, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, time) == 208, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, sunDirection) == 224, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, brdf) == 272, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, inverseViewProjection) == 288, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, ambientMode) == 352, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, haze) == 368, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, hazeSky) == 384, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, atmosphere) == 400, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, windDirection) == 416, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, windGust) == 432, "FrameData alignment drifted.");
#endif
```

| Fields | Added in | Read by |
| --- | --- | --- |
| `view`, `projection`, `viewProjection`, `cameraPosition` | 10 | Every 3D vertex shader, and the shading that needs the eye |
| `time`, `deltaTime` | 10 | No shader: the passes that animate (particles, grass, sea) carry their own time in their own parameter blocks |
| `sunDirection`, `sunColor`, `ambientColor` | 11 | The mesh shaders of 11 and 15. From 16 the light buffer replaces them there; Meshes, the scene graph, and the USD viewer still fill them, to build their sun's light from the panel. From 36 Horizon's own shaders read them again (`Terrain.frag.glsl`, `HorizonShading.glsl`), and from 41 the sea's surface on the coast |
| `brdf` | 15 | The mesh, G-buffer, and deferred lighting shaders |
| `inverseViewProjection` | 22 | The deferred lighting pass |
| `ambientMode` | 24 | The mesh and G-buffer shaders, and the grass's ground and blades (Chapter 25, section 8) |
| `haze`, `hazeSky` | [Renderer convergence](Tutorial/RendererConvergence.md#shared-distance-haze), after 39 | The mesh and deferred lighting shaders, the grass blades, and the sea's surface; Horizon writes them, while its terrain, plates and impostors haze from their own push constants |
| `atmosphere` | 51 | Shared physical-atmosphere sampling and solar attenuation at supported mesh, deferred, terrain, foliage and Sea surface hooks; disabled on the historical camera-only Ocean route |
| `windDirection`, `windGust` | 42 | Written by the Grass and Horizon demos from their `WorldWind`; zero, which is calm, everywhere else. No shader reads them yet: the grass's compute pass gets its copy through `GrassParameters`, where `PackParameters` hands calm on as no gusts with a gust size it can divide by (Chapter 42, section 1), and from section 2 the gust offset in `windDirection.zw` |

Before Renderer convergence the block was 368 bytes, and 40 of them no
shader read: 32 of padding, and the 8 of `time` and `deltaTime`, kept for the
first shader that animates by them. Chapter 16 retired the three sun and
ambient fields (48 bytes) from the mesh shaders, but Horizon's shaders read
them again from Chapter 36 on, so they are no longer dead weight. The
append-only rule keeps every field where it is, because removing one moves
every field after it; removing `time` and `deltaTime` once, on purpose, with
every shader that includes the block rebuilt, is a cleanup the book leaves
for you. Renderer convergence appends 32 bytes for the shared haze contract
and alignment, without changing earlier offsets. Chapter 51 appends another
16 bytes for atmosphere, taking the block to 416 bytes, and Chapter 42
appends 32 for the world wind, taking the current block to 448 bytes.
Chapter 51 is a side branch, so a reader can reach 42 without it; 42's
offsets assume 51's `atmosphere` at 400, and Chapter 42, section 1 says what
to do without it. Earlier chapter-stage
listings retain their then-current block size; do not mix an old stage's
uniform allocation with the current shader ABI. Rebuild every dependent shader
when moving a project to Renderer convergence, the atmosphere route or the
world wind.

### Named, not built

Every chapter that stops short of something says so where it stops. Here they
are in one place, grouped, each with the chapter or section it belongs to.

**Patterns already converged.** These were once on this list and are now
built, so do not extract them a second time from an older chapter's
description of the demos. The reference builds every demo's `FrameData`
through one helper, `makeFrameData` in `FrameData.h`, and shares the sun's
construction. Cubes, the particles and Ocean own the camera-only
`FrameBindings` rather than a whole `SceneRenderer` with materials and
shadows they never use. Sea keeps its `SceneRenderer` on purpose: its
imported rock and boat use the shared materials, lighting and shadows.

Renderer convergence, after Chapter 39, shares mesh ownership and instance
identity, preserves explicit depth conventions, and prepares independent view
and shadow-cascade visibility lists.
Specialized terrain, water and vegetation passes remain Vulkan passes; sharing
their contracts does not require forcing them into one universal shader.

**Smaller things in the engine.**

- `FrameData`'s unread `time` and `deltaTime` (above).
- The cubes and the particles' ground remain intentionally unlit. Meshes,
  the scene graph, the USD viewer, grass and Sea props use the lighting route
  appropriate to their materials. The water still has its own surface shader;
  sharing object shading does not automatically add water shadow reception.
- A third particle system — rain on the sea, smoke from the boat — is the time
  to move `SprayParticles` into `VulkanGraphics` as `GpuParticles` (31).
- Shader hot reload, and the deletion queue it needs (Chapter 6, section 8): with sliders
  already in place, it closes the iteration loop, and it is the single most
  useful addition.
- A render graph (Chapter 29, [Where to go from here](Tutorial/29-FFT-Ocean.md#where-to-go-from-here); ROADMAP defers it), once the
  demos have shown what passes need.
- A per-node "something below me changed" flag, so the transform update skips
  still subtrees (Chapter 12, section 4).
- Object names and command-buffer labels from `VK_EXT_debug_utils`, which the
  engine and its listings leave out by design (Chapter 34, section 7).
- The grass's ground and the horizon's terrain share a grid and a noise, and
  the sea and the horizon share a water shader. These are copies in chapters
  25, 27, 29, 30, 36 and 37 (Chapter 36, sections 3, 6, 10 and 11; Chapter 37, section 6, whose
  woods' noise is Chapter 36, section 3's lattice with a value at each point). Chapter
  41 shared part of it: its coast plants the Grass demo's `GrassField` on the
  triangles the rings draw and reuses the Sea demo's `SeaSurface`, but the
  Grass demo's own ground and the open sea in Horizon's `Terrain.frag.glsl`
  are still copies. Chapter 40 places its far forest on the CPU
  (`Terrain::TreeInCell`), not on the GPU from 37's `ForestDensity.glsl`, so
  it did not become the noise's next user; extract one module when the next
  real user appears.
- The upload with a mip chain (a staging buffer, a copy into level 0, a blit per
  level) is written three times: Chapter 15's `uploadTexture`, Chapter 36's
  `UploadHeightmap` and Chapter 38's `uploadLayers`, which adds layers. Make it
  one function, taking a format, a layer count and the stages that read the
  result, when a fourth copy appears.
- The generate, append and indirect-draw pass is now written three times:
  Chapter 21's particles, Chapter 26's grass and Chapter 39's understory (Chapter 39, sections 9–10). Extract it when a fourth appears.
- `coverageScales` (Chapter 39, section 6) averages a picture's mip levels on the CPU, for
  analysis only; the GPU's blits still make the levels it samples.

**Rendering.**

- Temporal anti-aliasing (Chapter 18, section 9; named again in Chapter 17, section 13, and in Chapters 22 and 27): shading
  aliasing and the grass's sub-pixel blades, which MSAA cannot fix.
- Transparency: sorted, in its own pass, or order-independent (Chapter 15, section 12).
- Many lights: tiled or clustered light lists for forward shading (Chapter 16, section 5);
  Forward+ (Chapter 22, section 1); 2.5D culling and clustered shading (Chapter 22, section 8).
- Shadows for spot, point, and area lights, and many shadowed lights (Chapter 17, section 14);
  soft shadows that widen with distance, PCSS (Chapter 17, section 10); a dithered cascade blend
  (Chapter 17, section 13).
- Energy lost to single-bounce GGX on rough metals, compensated (Chapter 24, section 8); the
  clouds in the sky's light (Chapter 24, section 9).
- Making every existing demo use reversed camera depth. The shared renderer
  now accepts an explicit depth policy; Horizon selects reversed depth while
  the other demos retain their taught conventional policy. Shadow maps remain
  conventional under either camera policy.
- `drawIndirectCount`, once something culls whole objects on the GPU (Chapter 19, section 7).
- A second occlusion pass against this frame's depth (Chapter 26, section 9).
- Many emitters counted on the GPU, emitter shapes (sphere, box, disc, a mesh's
  surface), bursts, sub-emitters, and color over life as a ramp: sketched in
  21's "Where to go from here" and left to you.

**The grass, the clouds, and the sea.**

- Short grass folded into two blades; screen-space shadows between blades; the
  blade's color, and its roughness, as a painted ramp (27).
- Clouds you can fly through, marched on screen with temporal reprojection; a
  round planet; cloud shadows on the ground; curl noise (28).
- A faster FFT, in shared memory or with subgroup shuffles (Chapter 29,
  [Where to go from here](Tutorial/29-FFT-Ocean.md#where-to-go-from-here)).
- Mipmaps for the small cascades; a denser grid near the camera; better foam;
  shallow water (Chapter 30, [Where to go from here](Tutorial/30-A-Rougher-Sea.md#where-to-go-from-here)), which Chapter 43 begins with gentle long waves on
  one coastal patch; shorter dispersive waves, bores and breaking are still
  to come (43, 44).
- Waves that know the rock is there; spray that lands as foam (31). A wake that
  follows the boat anywhere; the wake as waves; a boat steered from the CPU (32).

**The path tracer.**

- A whole USD scene: a BLAS per mesh, its materials and textures (Chapter 33, section 6).
- Next-event estimation, low-discrepancy samples, a glossy BRDF with its own
  pdf, and wavefront path tracing (Chapter 33, section 8).
- Ray tracing pipelines, route C (Chapter 33, section 7).

**Vulkan you have not used yet.** Timeline semaphores (Chapter 4, section 3;
Chapter 29, [Where to go from here](Tutorial/29-FFT-Ocean.md#where-to-go-from-here)); async
compute on a second queue, with ownership transfers; `VK_EXT_shader_object`;
graphics pipeline libraries; mesh shaders; `VK_EXT_descriptor_buffer`;
descriptor indexing. And Slang, when a material system starts wanting generics.

USD composition (Chapter 13, section 11) and subdivision surfaces (14) are not on the list on
purpose: the importer reads one file as Blender writes it, and says so in the
log when a file asks for more.

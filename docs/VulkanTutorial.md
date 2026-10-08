# PillowFort Vulkan Tutorial

A ground-up Vulkan refresher, written against **this** repository: its module
names, its Premake workspace, and the demos it exists to host.

[ROADMAP.md](../ROADMAP.md) says *what* the foundation is and *why*.
This tutorial is the missing *how* — the Vulkan concepts behind each checklist
item, with code that compiles against Vulkan 1.3 core. Read ROADMAP's Steps and
Guardrails once before you start, about ten minutes: every chapter's header
names its step, and the chapters cite the Guardrails by number.

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

You should be at home in C++20: designated initializers, `std::span`,
`std::format`, and RAII appear from Chapter 02 on without introduction. You do
not need a graphics or math background beyond high school; the next section
says what is taught, and where.

Every chapter ends with an **exit check**: things to run, look at, or break on
purpose, each with what you should see. Chapters 02-04 build pieces that
nothing runs until Chapter 05's frame loop exists, so their runtime checks say
to do them after Chapter 05. From Chapter 05 on, every check is something you
run and observe. Each chapter's header names its step in
[ROADMAP.md](../ROADMAP.md).

---

## What you need, and what it teaches

### To build and run it

- **This repository**, which the chapters write into. It already holds
  `GenerateProjects.bat` and Premake (Chapter 01 wires them up), a placeholder
  `SandboxGame/Main.cpp` (Chapter 05 replaces it), the older
  `VulkanGraphics/Camera/` (Chapter 10 compares its own camera against it), and
  `ErrorReporting/Log.h`: three static functions, `Log::info`, `Log::warning`,
  and `Log::error`, each taking a `const char*`, which the chapters call as
  `Log::error(std::format(...).c_str())`. Everything else in `VulkanGraphics`
  is what Chapters 02-08 write.
- **Windows 10 or 11, x64**, with **Visual Studio 2022** (the "Desktop
  development with C++" workload) and PowerShell. Premake is in the repository;
  Chapter 01 wires it up.
- **The Vulkan SDK**, with `VULKAN_SDK` set. The code was checked against
  1.4.357.
- **git**, for the submodules: GLFW and ImGui from Chapter 01, TinyUSDZ from
  Chapter 13.
- **A GPU with Vulkan 1.3** — dynamic rendering, synchronization2, and a
  `D32_SFLOAT` depth format you can sample — which means any desktop GPU of the
  last several years with a current driver. Chapters 02 and 10 check at
  startup and name what is missing. Anisotropic filtering (15) and multi-draw
  indirect (19) are optional in the spec and present on every desktop GPU. The
  one real hardware requirement is ray query, and only for the path tracer's
  route B (33); its route A runs anywhere.
- **Later, and optional:** Python 3 for the short scripts that write test
  scenes (15, 17, 19, 22, 23, 31); Blender 4.5 to make your own USD scenes (14,
  16); and RenderDoc, which Chapter 06's exit check asks for (Chapter 34
  sections 1-3 are a short walkthrough of it on this engine's frame).

### How long it is

| Arc | Chapters | Length | At the end you have |
| --- | --- | --- | --- |
| The foundation | 01-08 | About 35,000 words. One sitting per chapter; two for 08. | A triangle with live ImGui controls, drawn through an HDR offscreen target |
| Scenes | 09-19 | About 140,000 words | A USD scene viewer with materials, lights, shadows, MSAA, and instancing |
| Compute, and the renderer it grows | 20-24 | About 81,000 words | Conway's Life and GPU particles; then deferred shading, a sky, and light from the sky, for the viewer and every 3D demo |
| Grass | 25-27 | About 50,000 words | A grass field toward *Ghost of Tsushima* |
| Clouds and the sea | 28-32 | About 105,000 words, the heaviest stretch: 28, 29, 30, and 31 each run past 3,000 lines | Clouds, an FFT ocean, and a rougher sea with spray and a floating boat |
| Light, and the toolbox | 33-34 | About 21,000 words. 33 has two routes; 34 is read in pieces | A progressive path tracer, and the debugging tools |

From Chapter 09 on, a chapter is one to three hours of reading (the longest,
28, about three) and several evenings of code. The long chapters are split into
parts inside one file. Each part ends with something that runs and a short
checkpoint, which is a good place to stop for the evening.

### The math you will meet

Through Chapter 28 the tutorial teaches the math it uses at the point it first
uses it, and assumes only high-school math: trigonometry, and vectors as arrows
with a length and a direction. Each passage puts the idea in words first, then
works one example with numbers, and later chapters point back to it instead of
teaching it again. Chapters 29 and 33 need more — complex numbers and the
Fourier transform for the ocean, probability and Monte Carlo integration for
the path tracer — and each opens with a primer on it. Read the primer before
the code.

[The math, chapter by chapter](#the-math-chapter-by-chapter), the first table
in the Reference section, lists every passage: use it to find one again, or to
see what is coming.

---

## Chapters

| # | Chapter | Covers | Step |
| --- | --- | --- | --- |
| 01 | [Environment and Build Wiring](Tutorial/01-Environment-And-Build.md) | SDK tour, the Premake workspace and when to regenerate it, linking the loader, GLFW and ImGui submodules, validation config | 1 |
| 02 | [Instance, Device, and Queues](Tutorial/02-Instance-And-Device.md) | Layers, debug messenger, the window, feature chaining, queue family selection | 3 |
| 03 | [The Swapchain](Tutorial/03-Swapchain.md) | Surface caps, format and present-mode choice, what sRGB is, recreation | 4 |
| 04 | [Commands and Synchronization](Tutorial/04-Commands-And-Synchronization.md) | Pools, frames in flight, the semaphore trap, sync2 barriers | 5 |
| 05 | [The First Frame](Tutorial/05-First-Frame.md) | Dynamic rendering, clear, present, resize survival | 6 |
| 06 | [Shaders and Pipelines](Tutorial/06-Shaders-And-Pipelines.md) | `glslc` as a premake prebuild step, shader modules, the graphics pipeline, the triangle | 7 |
| 07 | [ImGui Debug Panels](Tutorial/07-ImGui.md) | Backend init under dynamic rendering, manual input forwarding, the frame-statistics panel | 8 |
| 08 | [Resources, Memory, and Descriptors](Tutorial/08-Resources-And-Descriptors.md) | Memory types, staging, images, the offscreen target and composite pass, descriptor sets, push constants, the ImGui-to-shader parameter path | 9 |
| 09 | [The Demo Harness](Tutorial/09-Demo-Harness.md) | The `Demo` interface, explicit registration in `SandboxGame`, an ImGui demo switcher, per-demo resize; the triangle becomes the first demo | 10 |
| 10 | [Cameras and Depth](Tutorial/10-Cameras-And-Depth.md) | Matrices, view and projection in Vulkan's clip space, fly and orbit controllers, the per-frame camera buffer, the depth buffer | 11 |
| 11 | [Meshes](Tutorial/11-Meshes.md) | Vertex input state, interleaved vertices, index buffers, uploading mesh data, winding and culling, per-draw transforms, one light | 12 |
| 12 | [The Scene Graph](Tutorial/12-Scene-Graph.md) | Nodes and transform hierarchies, dirty flags, flat draw lists, cameras as nodes, an ImGui hierarchy and inspector | 13 |
| 13 | [Adding a Library: TinyUSDZ](Tutorial/13-Adding-TinyUSDZ.md) | The recipe for any third-party library here, USD's core ideas, loading a stage | 14 |
| 14 | [Importing USD Scenes](Tutorial/14-Importing-USD-Scenes.md) | Prims to nodes, triangulation, primvars, up axis and units, USD cameras | 15 |
| 15 | [Materials and Textures](Tutorial/15-Materials-And-Textures.md) | `UsdPreviewSurface`, texture loading, mipmaps, samplers, per-material descriptor sets, tangents | 16 |
| 16 | [Lights](Tutorial/16-Lights.md) | UsdLux lights as nodes, light buffers, forward shading, light units, exposure and tone mapping | 17 |
| 17 | [Shadows](Tutorial/17-Shadows.md) | Shadow maps for the sun, depth bias and filtering, cascaded shadow maps for large outdoor views | 18 |
| 18 | [Anti-Aliasing](Tutorial/18-Anti-Aliasing.md) | MSAA under dynamic rendering, resolve attachments, sample counts, alpha-to-coverage; what MSAA cannot fix | 19 |
| 19 | [Instancing and Indirect Draws](Tutorial/19-Instancing-And-Indirect.md) | Per-instance storage buffers, USD instancing, indirect draw buffers | 20 |
| 20 | [Compute Fundamentals](Tutorial/20-Compute-Fundamentals.md) | Compute pipelines, the execution model, storage buffers and images, barriers between dispatches | 21+ |
| 21 | [GPU Particles](Tutorial/21-GPU-Particles.md) | Emit and simulate in compute, atomics, compaction, compute-written indirect draws, blending, and GPU timestamp queries to see what each pass costs | 21+ |
| 22 | [Deferred Shading](Tutorial/22-Deferred-Shading.md) | A G-buffer, lighting in a compute pass with tiled light culling, a live switch between forward and deferred, and when each wins | 21+ |
| 23 | [The Sky](Tutorial/23-The-Sky.md) | A sky behind every 3D demo, chosen in one engine setting: cube maps and their face order, lat-long environment images and USD dome lights, an analytic daylight sky from the sun, and the depth-1.0 trick that draws it last, forward and deferred | 21+ |
| 24 | [Image-Based Lighting](Tutorial/24-Image-Based-Lighting.md) | The sky as the scene's light: a diffuse cube and a specular cube with a level per roughness, filtered by compute whenever the sky changes, GGX's split-sum lookup table, Chapter 15's three BRDFs side by side, both of Chapter 22's paths, USD dome lights, and Chapter 21's timestamp queries made into a class | 21+ |
| 25-27 | Grass ([I](Tutorial/25-Grass-Blades.md), [II](Tutorial/26-Grass-GPU-Generation.md), [III](Tutorial/27-Grass-Look.md)) | Blade geometry, GPU generation, culling and LOD, clumping, wind, and shading, toward *Ghost of Tsushima* | 21+ |
| 28 | [Clouds](Tutorial/28-Clouds.md) | Participating media and Beer-Lambert, a ray march into a cloud cube of its own drawn over Chapter 23's sky, Henyey-Greenstein and multiple scattering by octaves, tileable Perlin-Worley noise in 3D images, a weather map, wind, and time slicing with a running average | 21+ |
| 29 | [The FFT Ocean](Tutorial/29-FFT-Ocean.md) | Complex numbers and the FFT, a GPU FFT tested on single waves, Tessendorf's spectrum, foam from the Jacobian, water shading | 21+ |
| 30 | [A Rougher Sea](Tutorial/30-A-Rougher-Sea.md) | Three FFT cascades whose bands never overlap, JONSWAP beside Phillips with fetch, directional spreading and a crossing swell, foam that lingers across frames, the engine's sky and clouds reflected with a normalized glint, a skirt to the horizon | 21+ |
| 31 | [Spray](Tutorial/31-Spray.md) | A rock in the sea, the water's height at a point by guess-and-correct, one probe set through which compute reads the sea, GPU-decided spray requests feeding Chapter 21's particles, a local foam map that does not repeat | 21+ |
| 32 | [A Boat](Tutorial/32-A-Boat.md) | Archimedes on hull columns, a rigid body moved on the GPU from the water it floats on, steering on the arrow keys, spray at the bow, a wake, a follow camera | 21+ |
| 33 | [Path Tracing](Tutorial/33-Path-Tracing.md) | Monte Carlo integration, a compute path tracer, accumulation, ray query and acceleration structures | 21+ |
| 34 | [Debugging and Profiling](Tutorial/34-Debugging.md) | RenderDoc on this engine's frame: taking a capture, reading the frame, finding our buffers by set, binding, and size; then GPU timing, reading validation messages, a lost device, object names and labels if you want them, a milestone checklist. A toolbox: sections 1-3 when Chapter 06's exit check asks for a capture, the rest when you need it | all |
| — | [The engine you built](#appendix-the-engine-you-built) | After Chapter 33: what owns what, one 3D frame in order, `FrameData` whole, and everything the book names but does not build | — |

**Routes.** By default the chapters are read in order, but not every chapter is
on every path:

- **Core:** 01-10 and 20.
- **Straight to the ocean or the path tracer**, after the core: 29, with
  Chapter 18 section 6 and Chapter 21 section 3; or 33's route A, with Chapter
  11 section 14, Chapter 15 section 9, Chapter 16 section 6, and Chapter 21
  section 3. [How to work through this](#how-to-work-through-this) says what
  each is for.
- **The renderer arc, in order:** 11-18, then Chapter 19 sections 1-8, then 21,
  22, 23, 24, and 28. Chapters 12-14 are engine work rather than Vulkan (a
  scene graph and a USD importer), but 15-19 need them.
- **Optional, and nothing on the default path depends on them:** the grass
  (25-27; if you skip it, read Chapter 27 sections 1 and 2 before 28); the
  rougher sea, spray, and the boat (30-32), a chain read in order; Chapter 19
  sections 9-11, USD instancing; and Chapter 33's route B.

**ROADMAP step 2**, the GLFW window and frame loop, has no chapter of its own,
which is why the Step column skips it. Read it in four places, in this order:
Chapter 02 section 4 (the `Window` module's `GlfwWindow` and its event queue),
Chapter 07 section 4 (registering the input callbacks), Chapter 05 section 3
(the loop body), and Chapter 10 section 10 (where the window's later additions
go). Closing is polled through `shouldClose`, not queued as an event, although
ROADMAP step 2's checklist lists close among the queued events.

### Where the code stands

Every chapter's code exists in full, implemented exactly as the text describes,
on the `reference-latest` branch, with the Windows pass's fixes. Compare
against it when your own version misbehaves. It is also
the complete listing: the chapters show code as it grows, each change with an
anchor saying where it goes, and collect a whole file in an appendix only where
it grew in pieces. For any file whole, read the branch. Its `REFERENCE.md`
records how each chapter was checked:

- **01-08** were built with MSVC at `/W4` with no warnings and run
  validation-clean on Windows with a GPU, with sync validation proven live and
  the chapters' claims read back from GPU pixels.
- **09-33** were built with g++ and run validation-clean on Linux (Mesa's
  lavapipe driver), with screenshots of their exit checks. `REFERENCE.md` says
  which have since had their run with MSVC on Windows and a GPU.
- **34** has no engine code: it reads the engine as built, in RenderDoc and in
  the validation layer's messages, and leaves object names and labels to you
  (Chapter 34 section 7). Its walkthrough follows RenderDoc's own
  documentation.

---

## How to work through this

Do not read it all first. The value is in hitting each exit check before
moving on.

A realistic pace:

- **Chapters 01-05**, one sitting each. This is the "prove the plumbing"
  phase, and the payoff is a colored window that survives resizing. Chapters
  02-04 have nothing to show on their own; Chapter 05 runs all of it. Resist
  adding anything.
- **Chapters 06-07** together. Once ImGui is up, everything after it is easier
  to debug, because you can put state on screen. Chapter 06's exit check asks
  for a RenderDoc capture; Chapter 34 sections 1-3 walk through one. Section
  3, finding our buffers, has more to find once Chapter 10 section 7 adds the
  per-frame buffer.
- **Chapter 08** is the one worth slowing down on. Buffers, images, and
  descriptors are where every later demo actually lives.
- **Chapter 09** is mechanical rather than conceptual, but not short: it builds
  the frame every later demo plugs into, so the chapters after it can each say
  "a demo" and mean one folder.
- **Chapters 10-19** are one arc, in order: a camera, then meshes, then a scene
  graph to hold them, then USD to fill it, then what makes it look real —
  materials, lights, shadows, anti-aliasing — then drawing a lot of it. Each
  exit check is something you can fly a camera around. Chapter 10 is where the
  math starts; take its first sections slowly.
- **Chapters 20 and 21** are the door to every compute chapter: Conway's Life,
  then GPU particles. Chapter 21 section 8 teaches GPU timestamp queries, which
  every later chapter that measures itself uses; Chapter 24 section 9 makes them
  a class.
- **Chapters 22-24** grow the renderer the 3D demos share: deferred shading
  (22), which the USD viewer can switch to; a sky (23), which every 3D demo can
  turn on; and light from that sky (24), which Meshes, the scene graph, and the
  USD viewer use.
- **The grass (25-27)** needs the particles (21), the sky (23 section 8), and
  its light (24 section 4). **The clouds (28)** build on the grass's noise; if
  you skipped the grass, read Chapter 27 sections 1 and 2 first, without
  building anything.
- **The ocean (29)** can be reached without 11-28: it needs Chapters 01-10,
  Chapter 18 section 6 (the scene's sample count), 20, and Chapter 21 section
  3's random numbers. The chapters after it bring things together and need
  more: 30 gives the sea more complex waves under the sky (23) and the clouds
  (28); 31 puts a rock in it, with spray from the particles (21) where the
  waves break and foam that stays; 32 floats a boat on it, a rigid body moved
  on the GPU, which also needs Chapter 10's quaternion and cross product.
- **The path tracer (33)** needs Chapters 01-10 and 20, Chapter 11 section 14
  (the dot product as Lambert's cosine), Chapter 15 section 9 for reading
  (radiance, irradiance, and Lambert's BRDF), Chapter 16 section 6 (the tone
  curve), and Chapter 21 section 3's random numbers and cone sampling; route B
  also uses parts of Chapters 08, 11, and 19. It needs nothing from the
  ocean or the grass. The ocean and the path tracer each open with a primer on
  their math, which no earlier chapter covers. If you built image-based
  lighting (24), 33's section 0 starts from 24 section 1's sum over the sky; it
  does not need it.
- **The rest of Chapter 34** is for when you need it: section 5 the first time
  a validation message puzzles you, section 6 the first time the device is
  lost, and section 8's checklist at every milestone. Section 7, readable any
  time after Chapter 09, explains object names and command-buffer labels from
  `VK_EXT_debug_utils`: what they change in captures and messages, and what
  they cost. Adding them is your choice; the reference engine and the chapters'
  listings have none, by design. They pay most in the grass, the clouds, and
  the sea, whose captures hold dozens of passes.
- **[The engine you built](#appendix-the-engine-you-built)**, the appendix at
  the end of this page, is for when you finish, or whenever you lose track of
  where something lives.

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
There is no hidden state and no reference counting. You fill a `Vk*CreateInfo`
struct, call `vkCreateX`, get an opaque 64-bit handle, and are personally
responsible for calling `vkDestroyX` before the device dies, in an order that
respects dependencies. `sType` is always the first member and always must be
set; `pNext` is how the API grew without breaking ABI.

**2. Objects live in a strict containment hierarchy.**

```text
Loader (vulkan-1.dll)
+-- VkInstance                 -- API version, layers, instance extensions
    +-- VkPhysicalDevice       -- a GPU as reported by the driver (never created or destroyed by you)
    +-- VkSurfaceKHR           -- a platform window, wrapped
        +-- VkDevice           -- your logical connection to one physical device
            +-- VkQueue        -- where work is submitted (never created or destroyed by you)
            +-- VkSwapchainKHR -- the ring of presentable images
            +-- VkImage / VkBuffer / VkDeviceMemory
            +-- VkPipeline / VkPipelineLayout / VkDescriptorSetLayout
            +-- VkCommandPool -> VkCommandBuffer
```

**3. Nothing executes when you call it.**
`vkCmd*` functions *record* into a command buffer. Recording is single-threaded
per command buffer and free-threaded across command buffers. Work begins only
at `vkQueueSubmit2`, and even then the queue is asynchronous — the CPU races
ahead unless you make it wait.

**4. Synchronization is entirely yours, and it has exactly three jobs.**

- **Execution dependency** — B must not *start* until A *finishes*.
- **Memory dependency** — B must *see* what A wrote. Writes must be made
  *available* (flushed out of A's caches) and then *visible* (invalidated into
  B's caches). These are two separate things and both barrier masks exist to
  express them.
- **Layout transition** — the driver may physically rearrange an image's memory
  depending on how it is about to be used.

A pipeline barrier does all three at once, which is why barrier code looks so
dense. The primitives:

| Primitive | Synchronizes | Typical use |
| --- | --- | --- |
| `VkFence` | GPU to CPU | "is frame N's command buffer done, so I can reuse it?" |
| Binary `VkSemaphore` | GPU queue to GPU queue | swapchain acquire / present handoff |
| Timeline `VkSemaphore` | GPU and CPU, many waiters | frame pacing, compute-to-graphics chains (not used in this tutorial) |
| Pipeline barrier | Everything earlier and later on one queue | layout transitions, compute ping-pong |
| Queue family ownership transfer | Between queue families | only if you add a dedicated transfer or compute queue |

**5. The GPU has no idea what your data means.**
A `VkBuffer` is a length and some usage flags. A `VkImage` is dimensions, a
format, and usage flags. Shaders reach them through **descriptors** (bound in
sets), **push constants** (inline, tiny, fast), or **device addresses** (a raw
64-bit pointer, the modern option). Getting data to a shader is a solved-once
problem — solve it deliberately in Chapter 08 and every demo after it gets
easier.

---

## What changed since the tutorials you probably remember

If your Vulkan memories are from the 1.0/1.1 era, roughly a third of the
boilerplate you remember is now optional or obsolete. This repo targets
**Vulkan 1.3 core**, which is where the good parts landed.

| You remember | Do this instead | Why |
| --- | --- | --- |
| `VkRenderPass` + `VkFramebuffer` + subpasses | **Dynamic rendering** via `vkCmdBeginRendering` and `VkRenderingInfo` | Deletes two object types and all the pipeline/renderpass compatibility rules. Core in 1.3. |
| `vkCmdPipelineBarrier`, `VkSubmitInfo` | **Synchronization2** via `vkCmdPipelineBarrier2`, `vkQueueSubmit2` | 64-bit stage and access masks, per-barrier stages, far fewer "which stage do I use" mistakes. Core in 1.3. |
| Baked viewport and scissor in the pipeline | `VK_DYNAMIC_STATE_VIEWPORT` and `VK_DYNAMIC_STATE_SCISSOR` | Pipeline survives window resize instead of being rebuilt. |
| A descriptor set written for every draw | Push constants for small per-draw data; sets grouped by how often they change — once per frame, once per material (Chapter 08 section 6) | Few sets, each written when its contents change rather than per draw. Descriptor indexing and buffer device addresses exist for when sets get in the way; in this book only the path tracer's route B needs one, a device address. |
| `vkGetPhysicalDeviceFeatures` | `vkGetPhysicalDeviceFeatures2` with `VkPhysicalDeviceVulkan1{1,2,3}Features` | One struct per API version instead of one per extension. |
| Fence per frame + `renderFinished` semaphore per frame | Fence per frame **in flight**, `renderFinished` semaphore per **swapchain image** | The classic per-frame present semaphore is a genuine validation error. Chapter 04 explains it. |
| Hand-rolled `vkAllocateMemory` per resource | Vulkan Memory Allocator | Ships in your SDK already. Chapter 08 allocates by hand once, then switches. |

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

### The math, chapter by chapter

Every passage that teaches a piece of math, in reading order. Each puts the
idea in words, works one example with numbers, and is pointed back to by the
chapters after it.

| Math | What it is for | Taught in |
| --- | --- | --- |
| Vectors: adding, scaling, length, normalizing | Positions, directions, colors | Assumed |
| The sRGB curve, and why light is added in linear | Every color you store or display | 03 §2, with numbers; 08 §4, the exact formula |
| Clip space, and values blended across a triangle | Where a vertex lands; the triangle's gradient | 06 §2 |
| Blending two values by a fraction: linear interpolation, `mix` | The sRGB curve's two pieces; later, everything that fades | 08 §4 |
| Byte layout: alignment and padding (`std140`, `std430`) | Structs shared between C++ and shaders | 08 §8 |
| A matrix times a point; its columns as where the axes land; composing right to left; `w = 1` points and `w = 0` directions | Moving things, cameras | 10 §1 |
| Perspective projection, read one row at a time; the divide by `w`; depth precision | The camera's picture | 10 §2 |
| Quaternions, used as a tool | Orientations | 10 §3 |
| The inverse of a matrix | The view matrix | 10 §4 |
| Yaw and pitch from `sin` and `cos` | Fly and orbit cameras | 10 §6 |
| The cross product | Normals, which side is the front | 10 §8; applied in 11 §4 |
| Winding seen on screen | Back-face culling | 11 §7, as pictures |
| Transpose; the normal matrix (inverse transpose); a rotation's transpose as its inverse | Normals under non-uniform scale | 11 §13 |
| The dot product as a cosine: Lambert's law | Diffuse light | 11 §14 |
| A column's length as its scale; the cross product in components; handedness; the determinant as a mirror test; the dot product with a unit vector as how far along it reaches, and Gram-Schmidt: making one direction perpendicular to another | Taking a matrix apart; a camera's frame | 12 §5, building on 10 §1 and §8 |
| A plane as four numbers; a matrix's rows read as planes; the frustum from a matrix | Culling | 12 §9, building on 10 §2 |
| Changing up axis and units with one matrix | Z-up and centimetre scenes | 14 §2 |
| Row vectors and column vectors, and how the 16 numbers are stored | Reading USD's transforms | 14 §3 |
| A lens's angle from `tan` of half of it; framing with `sin θ = r / d` | USD cameras; a camera that fits the scene | 14 §6, §9 |
| Mip levels and `log2`; screen-space derivatives from 2x2 quads | Textures seen from far away; `fwidth` | 15 §5 |
| Radiance and irradiance; Lambert's 1/π; Schlick's Fresnel; three BRDFs side by side (Lambert, normalized Blinn-Phong, and the GGX microfacet model with Smith's G), each as an equation and as code | Physically based materials, and a live toggle between the models | 15 §9 |
| The tangent frame, made perpendicular with Gram-Schmidt | Normal maps | 15 §10, from 12 §5 |
| Solid angle; light units (lux, candela, watts); inverse-square falloff; color temperature | USD's lights | 16 §2 |
| Fading between two values (`smoothstep`) | A spot light's edge; later, level of detail without popping | 16 §5, with a worked number; again in 26 §6 |
| Exposure in stops; tone curves | Bright scenes on a display | 16 §6 |
| Orthographic projection; a box around a frustum | The sun's shadow camera | 17 §1-2 |
| Normalized device coordinates | Looking a point up in the shadow map | 17 §6 |
| Depth-bias slope | Shadow acne | 17 §7, in words with a worked number |
| Uniform and logarithmic splits | Shadow cascades | 17 §11 |
| An enclosing sphere; snapping to texels | Shadows that hold still | 17 §12 (the algebra is optional) |
| Samples and coverage | Anti-aliasing | 18 §1-2 |
| Coverage from `fwidth` | Soft cutout edges | 18 §8, building on 15 §5 |
| Hashing integers into uniform random numbers | Randomness on the GPU | 20 §3; refined in 21 §3 |
| Uniform random directions in a cone; stepping motion through time (Euler); exponential drag | Emitting and simulating particles | 21 §3 |
| View space | Camera-facing billboards | 21 §5 |
| Premultiplied alpha | Blending particles | 21 §5 |
| Little's law | How many particles are alive | 21 §7 |
| Depth back to view distance | Soft particles | 21 §10 (exercise) |
| Cost as a product: pixels × overdraw × lights; bytes per pixel as bandwidth | Choosing forward or deferred | 22 §1 |
| Octahedral encoding: a unit vector in two numbers | Normals in the G-buffer | 22 §3 |
| Position from depth: the inverse view-projection and the divide by `w` | Lighting a pixel from the G-buffer | 22 §5 |
| Planes through the eye from two projection entries; a sphere against a plane | Tiled light culling | 22 §8, building on 12 §9 |
| Positive floats ordered like their bit patterns | A min and max with integer atomics | 22 §8 |
| A pixel's direction: un-projecting through the inverse of projection × rotation | The sky behind everything | 23 §1 |
| Cube-map faces: the largest component picks the face; each face's right and down | Storing and sampling a sky | 23 §2 |
| Latitude and longitude of a direction, both ways | Environment images, USD dome lights | 23 §4 |
| A flat label on a sphere: dividing by the forward component | The test environment | 23 §5 |
| A disk's solid angle; the radiance that delivers an irradiance, L = E / Ω | The sun's disk | 23 §6, from 16 §2 |
| Σ and ∫, the book's first: "add up the term for every piece", and the same for infinitely many infinitely small pieces; light on a surface as a cosine-weighted sum over the whole sky, stored as E / π | Ambient light from a sky | 24 §1 |
| The solid angle of a cube texel, area / d³ | Adding up a sky stored in a cube | 24 §2 |
| A weighted average over a lobe; splitting one sum into two (the split-sum approximation) | Reflections of a sky at every roughness | 24 §5-6 |
| A lobe's share within an angle; points placed by equal shares (importance sampling without random numbers) | The specular lookup table | 24 §7 |
| Jittered grids | Placing blades | 25 §2 |
| A normal from two slopes | The ground's shading | 25 §3 |
| Cubic Bézier curves and their tangents | A blade's shape and normal | 25 §6-7 |
| A pyramid of farthest depths; choosing its level with `log2` | Occlusion culling | 26 §9 (optional) |
| Voronoi cells; gradient noise | Clumps; wind | 27 §1, §2 |
| Pixels per metre from the projection | A minimum blade width | 27 §4 |
| Light through a thin surface; a highlight in Blinn-Phong and in GGX | The grass's shading, with its own toggle | 27 §7, from 15 §9 |
| Density and extinction; mean free path; the number e and `exp`; Beer-Lambert's law, T = e^(−σd); optical depth | How much light gets through fog and cloud | 28 §2 |
| A ray against a horizontal plane, t = (h − y) / d_y; a march as a sum of thin slices; one step's exact integral, S × (1 − e^(−σΔs)); jittering the start | Marching through the cloud layer | 28 §3 |
| Phase functions; Henyey-Greenstein, one lobe and two | Which way a droplet scatters light; the silver lining | 28 §6 |
| A 3D image's memory (n³; a 3D mip chain adds 1/7); Worley noise as the distance to the nearest Voronoi point, in 3D; noise that tiles; Perlin-Worley | Cloud shapes | 28 §7, building on 27 §1-2 |
| Remapping a range onto [0, 1]; coverage as one subtraction; a height profile from two smoothsteps | Cloud density | 28 §9 |
| A mip level from a footprint (log2 of metres per texel), without derivatives | Sampling far clouds in a compute shader | 28 §9, building on 15 §5 |
| Multiple scattering as a sum of octaves | White clouds with the sun behind you | 28 §11 |
| A color's luminance as one number, 0.2126 R + 0.7152 G + 0.0722 B | How bright a white cloud should be | 28 §11 |
| The exponential moving average: its noise (a variance), w / (2 − w), and its lag, (1 − w) / w | Hiding a march's noise; ghosting | 28 §13 |
| Complex numbers as arrows; multiplying turns them | Waves with amplitude and phase | 29 §1 |
| The inverse discrete Fourier transform; the FFT (butterflies, bit reversal) | Adding up every wave at once | 29 §2 |
| Gaussian random numbers (Box-Muller, which uses `ln`, the inverse of `exp`); the Phillips spectrum | The sea's starting waves | 29 §7 |
| The deep-water dispersion relation; differentiating a wave by multiplying by i k | Waves in motion, slopes, sharp crests | 29 §8 |
| The Jacobian: how much a small square is squeezed; the determinant of 12 §5 | Foam | 29 §9 |
| Fresnel (Schlick) | Water's reflection | 29 §10, from 15 §9 |
| A repeat distance as a common multiple | Why one patch tiles; choosing patch sizes | 30 §1 |
| Wavelength, wave number, and texels per wave; bands that do not overlap | Splitting waves between cascades | 30 §2 |
| A spectrum over frequency turned into one over wave vectors (dω/dk, 1/k); the area under a curve in strips; Hs = 4√m0 | JONSWAP | 30 §5 |
| A function of direction normalized by summing it | Directional spreading | 30 §6 |
| A narrow peak sampled by a coarse grid | A swell in a cascade | 30 §7 |
| Exponential decay and its half-life, τ ln 2 | Foam that lingers | 30 §8, from 21 §3 and 28 §2 |
| Normalizing a cos^p lobe around the reflection, (p+1)/2π | The sun's glint in the sun's units | 30 §10, beside 15 §9's Blinn-Phong factor |
| Premultiplied over: sky × (1 − a) + cloud | Clouds in the water | 30 §10, from 21 §5 |
| Fixed-point iteration: guess, see where it lands, correct by the miss | The water's height above a place | 31 §3 |
| A speed as the change over one frame | How fast water comes at a rock | 31 §5 |
| Rounding at random so the average comes out right | How many particles to ask for | 31 §6 |
| Archimedes' principle, F = ρgV, a column at a time | Floating | 32 §1 |
| Torque r × F; moment of inertia, m(a² + b²)/12 for a box; τ/I in a body's own axes; a rotation's transpose as its inverse | A rigid body | 32 §2, building on 10 §8 and 11 §13 |
| The velocity of a point on a turning body, v + ω × r | Drag on the hull; the boat's spray | 32 §2 |
| A spring's bob, √(k/m); a quaternion turned by an angular velocity, q + (h/2)(ω,0)q, normalized; substeps for a stiff spring | Moving the boat | 32 §2, from 21 §3 |
| A ray against a sphere: a quadratic in t | What each of the path tracer's rays hits | 33 §3 |
| Probability, Monte Carlo integration, importance sampling, pdfs, Russian roulette | The path tracer | 33 §0, §4 (importance sampling first met, without randomness, in 24 §7) |

### Color, across the whole tutorial

Color handling is decided in one chapter and paid for in four others, so here is
the whole plan in one place. Chapter 03 section 2 shows what the sRGB curve does
to numbers, with a worked example.

**The model.** Every color is in one of two encodings. *Linear* is where
lighting math is correct — adding, averaging, and multiplying light only work
there. *sRGB-encoded* is what the display expects and what 8-bit images store.
The plan is to keep everything the scene computes linear and to convert to sRGB
**exactly once**, at the end.

```text
 inputs ──linear──▶ scene shaders ──linear──▶ R16G16B16A16_SFLOAT scene target
                                                         │
                                  composite pass: exposure, tone map, clamp, encode
                                                         ▼
 ImGui (already sRGB) ─────────────────────────▶ B8G8R8A8_UNORM swapchain ──▶ display
```

**Who does the encode, chapter by chapter:**

| Chapter | Swapchain | Encoder | What you see |
| --- | --- | --- | --- |
| 03-06 | `B8G8R8A8_SRGB` | The hardware, on every write | Correct. The clear color and triangle are linear values encoded once. |
| 07 | `B8G8R8A8_SRGB` | The hardware — including on ImGui's bytes, which are already sRGB | ImGui looks pale: its colors are encoded a second time. Expected, and left alone for one chapter. |
| 08 | `B8G8R8A8_UNORM` | The composite pass | Scene correct; ImGui correct, because the UNORM image stores its bytes untouched. The triangle looks as it did in 06 — the check that the switch worked. |
| 16 | `B8G8R8A8_UNORM` | The composite pass, now with exposure and a tone curve | Physical light values — and later the path tracer's HDR output — compress into range instead of clipping. Defaults reproduce 08 exactly. |

**Why switch at 08 rather than start there.** An `_SRGB` swapchain is the
least code that is correct for chapters 03-06, and the offscreen target that
makes UNORM work arrives in 08 for its own reasons: every scene from Chapter 10
on renders into an HDR image, and Chapter 16's tone curve reads it. Switching is
one constant in `chooseSurfaceFormat`. The price is one chapter of pale ImGui.

**Why not the alternatives.** Keeping `_SRGB` and correcting ImGui's style
colors makes every color picked from a reference wrong. A UNORM swapchain with
no composite pass means every final shader must remember to encode. A
mutable-format swapchain with both an sRGB and a UNORM view works, but needs an
extension to solve what the offscreen target already solves.

**The three rules that follow from it** — Chapter 08 section 4 has the full
table:

1. Everything entering the scene must arrive linear. Color textures are created
   `_SRGB` so sampling decodes them; data textures are `UNORM` or `SFLOAT`.
2. Anything ImGui displays stays in sRGB bytes: images shown only through
   `ImGui::Image` are `UNORM`, and colors picked with `ColorEdit` are sRGB and
   must be converted before the scene uses them.
3. Only the composite pass encodes. If the surface ever forces an `_SRGB`
   swapchain, its `encodeSrgb` specialization constant turns the shader's
   encode off so nothing is encoded twice.

### Cameras, geometry, and scenes, across the tutorial

Like color, these are decided once and then used by every chapter from 10 on.
Each row names the chapter that teaches it; this table is only the summary.

**Conventions.**

| Thing | Convention | Taught in |
| --- | --- | --- |
| World space | Right-handed, +Y up, one unit is one metre | 10. A USD stage that is Z-up or in centimetres is converted once, at import (14). |
| View space | The camera sits at the origin looking down −Z, +Y up — what `glm::lookAt` builds | 10 |
| Clip space | Vulkan's: +Y points down, depth runs `[0, 1]`. The projection matrix negates `[1][1]`, and `GLM_FORCE_DEPTH_ZERO_TO_ONE` (premake) gives `[0, 1]`. Nothing else flips Y — not the viewport, not the shaders | 10 (06 previewed it) |
| Depth | `D32_SFLOAT`, cleared to `1.0`, compared with `LESS`. Reverse-Z is explained as an aside and not used | 10 |
| Winding | Meshes are counter-clockwise seen from the front, as in USD, glTF, and OpenGL. The projection's Y flip keeps the picture upright, so they are counter-clockwise on screen too: `frontFace = COUNTER_CLOCKWISE`, `cullMode = BACK`. The triangle from 06 stays `CLOCKWISE`, because its positions are written straight into Vulkan's Y-down clip space with no projection | 11 |
| Indices | `uint32_t` | 11 |
| The sun's direction | The way sunlight *travels*, from the sun toward the scene (`sunDirection`); code that needs the opposite names it `toSun` | 11, 16 |

**Where the code lives.**

| Module | Namespace | Holds |
| --- | --- | --- |
| `Source/PillowFort/Scene/` | `pf::scene` | CPU-side and Vulkan-free: `Transform`, `Camera`, the fly and orbit controllers (10); `Vertex` and `MeshData` (11); `Scene` and its nodes (12); materials (15) and lights (16) as plain data |
| `Source/PillowFort/VulkanGraphics/` | `pf::vulkan_graphics` | The GPU side of the same things: the per-frame buffer (10), mesh upload (11), material descriptor sets (15) |
| `Source/PillowFort/UsdImport/` | `pf::usd_import` | The only code that includes a TinyUSDZ header (13, 14) |
| `Source/PillowFort/Demos/<Name>/`, `Shaders/<Name>/` | per demo | Anything one demo needs and the next would not |

**Names.** Member functions are PascalCase (`Camera::Projection`) in
`VulkanInstance` (02) and in every class from Chapter 09 on (`Demo`,
`SceneRenderer`, `Sky`, ...): the engine's house style. The other classes of
Chapters 02-07 — `InitializationResult` and `GlfwWindow` (02),
`VulkanSwapchain` (03), `VulkanRenderer` (04), and `ImGuiDebugPanels` (07) —
keep lowercase names, like the older `Log`, including what later chapters add
to them (`renderer.setSampleCount`, 18), until they are converted as a whole. Free functions are camelCase (`createBuffer`,
`uploadMesh`, `computeBounds`), except UsdImport's two entry points,
`ImportUsdFile` and `LogUsdPrimTree`.

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

**Descriptor sets.** Chapter 08 section 6 introduced the idea of grouping by how
often things change. From Chapter 10 on it is concrete:

| Set | Bound | Contents | From |
| --- | --- | --- | --- |
| 0 | once per frame | everything every draw in the frame shares; its bindings are listed below | 10, grown by 16, 17, 19, 22, and 24 |
| 1 | per material | binding 0: material parameters; bindings 1 and up: its textures | 15 |
| the sky (23) | its own layout | set 0, binding 0: the sky cube (`samplerCube`); push constants: `SkyDrawParameters`. Draw it last in a scope, or rebind your sets after it | 23 |
| push constants | per draw | the model matrix (and later a material or instance index) | 11 |
| set 0, binding 2 | per instance | transforms indexed by `gl_InstanceIndex`, one buffer per frame in flight, replace the per-draw push constant. Compute-generated instances (21 onward) use their own buffers and layouts | 19 |

Set 0's bindings, and the chapter that adds each:

- **binding 0:** the frame uniform buffer, `FrameData` — `view`, `projection`,
  `viewProjection`, `cameraPosition`, and time (10); `inverseViewProjection`
  (22); `ambientMode` (24). The appendix shows it whole.
- **binding 1:** the light storage buffer (16).
- **binding 2:** the per-instance storage buffer (19).
- **bindings 3 and 4:** the shadow cascades' uniform buffer and the cascaded
  shadow map, a `sampler2DArrayShadow` (17).
- **bindings 10-12:** the sky's light — the diffuse cube and the specular cube
  (`samplerCube`), and the split-sum table (`sampler2D`) (24).
- **bindings 5-9** stay free: Chapter 22's lighting set reuses set 0's numbers
  and puts its own images there.

The frame block's C++ and GLSL twins live in `Shaders/Include/SharedShaderTypes.h`,
the shared header Chapter 08 section 8 sets up. Compute passes (20 onward) use
their own layouts; nothing above constrains them.

**Who owns what in a frame.** The appendix draws all of it; these are the rules.

- **The engine owns the window-sized images.** `VulkanRenderer` owns the scene
  color target (08), the single-sample scene depth (10, created with `SAMPLED`
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
- **The scene part of the frame belongs to the demo**, exactly as Chapter 08
  section 4's contract says: the demo receives the scene target and hands it
  back in `SHADER_READ_ONLY_OPTIMAL` with its writes visible to the fragment
  shader, and everything in between is its business — compute dispatches,
  shadow passes, a rasterized pass, more drawing after it. A rasterizing demo
  opens its pass through an engine helper that sets up the color, depth, and
  (from Chapter 18) multisample-resolve attachments, so the resolve logic
  exists once; a compute demo such as the path tracer never calls it. The
  demo's `record` is told which frame in flight it is recording, and runs after
  that slot's fence has been waited on.
- **Drawing a `pf::scene::Scene` is a reusable class** in `VulkanGraphics` — it
  owns set 0's layout and per-frame buffers, the mesh pipelines, and the
  recording of a draw list — introduced in Chapters 10-12 and grown by 15-19 and 22
  (materials, lights, shadows, sample count, instancing, and the deferred path,
  whose G-buffer it rebuilds when the demo's `Resize` passes the new targets
  on). A demo that shows a scene owns one. A demo with its own pipelines owns
  one too and binds its set 0 into them: the grass also draws its stones and
  shadows through it, while Cubes, the particles, the ocean, and the sea use
  nothing else of it (the appendix's second seam).

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
already ship inside the Vulkan SDK you have installed**, at
`%VULKAN_SDK%\Include\{glm,vma,Volk}`. Adopting one is an `includedirs` line,
not a submodule, a build-system change, or a license question.

| Dependency | Recommendation | Reasoning |
| --- | --- | --- |
| **GLM** | Already in (the `Camera` module uses it) | `GLM_FORCE_DEPTH_ZERO_TO_ONE` encodes Vulkan's `[0, 1]` depth convention, which you would otherwise rediscover painfully. Define it once in `premake5.lua` (Chapter 01's workspace does), never per file — Chapter 06 section 2 says why. It does not handle the Y flip; Chapter 10 section 2 does. Current GLM uses radians unconditionally, so `GLM_FORCE_RADIANS` is no longer needed. |
| **VMA** | Hand-roll allocation once, then switch, both in Chapter 08 | Allocating memory yourself exactly once is genuinely instructive: heaps, memory types, alignment, and mapping. Doing it for the dozens of buffers and textures a scene needs is not, because at that point you are writing a suballocator, which is not a Vulkan learning goal. |
| **Volk** | Skip; reconsider for Chapter 33 route C | You link `vulkan-1.lib` directly and target one platform. Volk buys loader-bypass dispatch and extension-function loading you do not need; route B loads its five ray tracing functions by hand. |

One place the roadmap's defaults are worth bending once the demos start:
**FIFO present mode** is right for the foundation and mildly annoying once you
have ImGui sliders, because it adds latency to every drag. Chapter 03 makes the
present mode a setting — from the command line at startup, from a Chapter 07
picker at runtime — because which modes exist depends on the GPU. The same goes
for the GPU itself on a machine with two (Chapter 02 section 5).

### Repository conventions this tutorial follows

Per [ROADMAP.md](../ROADMAP.md):

```text
VulkanGraphics
  path:      Source/PillowFort/VulkanGraphics
  namespace: pf::vulkan_graphics
  include:   PillowFort/VulkanGraphics/VulkanInstance.h
```

- Backend-specific types carry their backend: `VulkanDevice`, `GlfwWindow`,
  `ImGuiDebugPanels`.
- Constructors do not perform fallible GPU work. Initialization returns a
  descriptive result type.
- Assertions are for programmer mistakes. Unsupported hardware and missing files
  are reported, not asserted.
- Exceptions do not cross module boundaries.

Code in this tutorial follows that style: initialization functions return a
result, and each chapter names its module up front. Where a snippet is not a
whole function, the section says which function it belongs to — Chapter 02's
"What you are actually writing" is the pattern the rest follow.

---

## Appendix: The engine you built

A reader's map for the end of the book, or for any time you lose track of where
something lives: what owns what, what one 3D frame does in order, the frame
block whole, and one list of everything the chapters name and do not build.
Nothing here is new; each line names the chapter that built it.

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
│   ├── SkySettings (+ CloudSettings)   23   handed to the demo in RecordContext; main draws the panel (28 adds the clouds')
│   ├── ImGuiDebugPanels                07   the backend, the frame panel, the present-mode, demo, and MSAA pickers
│   └── the active Demo, borrowed       09
└── every Demo, one push_back each      09   switched by the picker; only the active one is set up
```

Each demo is a folder under `Demos/` and owns its GPU objects from `Setup` to
`Teardown`. What each one owns, besides its own pipelines:

```text
Triangle, Gradient    09      a pipeline and its push constants (the triangle's moved here from VulkanRenderer)
Cubes                 10      SceneRenderer (for set 0 only), Sky
Meshes                11      SceneRenderer, Sky
Scene graph           12      SceneRenderer, Sky, a pf::scene::Scene and its panels
USD viewer            14-24   SceneRenderer, Sky, a Scene imported by UsdImport, light glows (22), its own timestamps (22)
Life                  20      two cell images, ping-ponged; a statistics buffer and its readback
Particles             21      SceneRenderer (for set 0 only), Sky, the particle pool and lists, its own timestamps
Grass                 25-27   SceneRenderer (stones, shadows), Sky, blade and counter buffers, a depth pyramid (26), GpuTimestamps (26)
Ocean                 29      SceneRenderer (for set 0 only), FFT images, a sky gradient of its own
Sea                   30-32   SceneRenderer (for set 0 only), Sky, three FFT cascades, GpuTimestamps,
                              SeaObjects: the rock and the boat, the probe set, spray requests, SprayParticles
Path tracer           33      the accumulation image; route B's MeshScene: buffers, BLAS, TLAS
```

The engine classes those demos compose, in `VulkanGraphics`:

```text
SceneRenderer           10-24   set 0, and a Scene's draw list, drawn
├── set 0               10      FrameData (10), lights (16), instances (19), shadow data and map (17), sky light (24)
├── geometry            11, 19  every mesh in one vertex buffer and one index buffer
├── materials           15      set 1 per material, textures, sixteen samplers, a white texture
├── mesh pipelines      11, 15  one per shading mode, opaque and cutout; a sample count from 18
├── batches             19      instancing and multi-draw indirect
├── ShadowMaps          17      the sun's cascades in one layered depth image
└── DeferredShading     22      the G-buffer, tiled light culling and lighting in compute

Sky                     23      owned by each demo that shows one: Update before the scene pass, Draw inside it
├── the sky cube        23      baked by compute only when its inputs change
├── ImageBasedLighting  24      diffuse cube, specular cube, split-sum table: set 0's bindings 10-12
└── Clouds              28      noise images, a weather map, a march into a cloud cube every frame

GpuTimestamps           24      used by ImageBasedLighting, Clouds, the grass, and the sea
```

Beside them, `pf::scene` holds everything Vulkan never sees — `Transform`,
`Camera` and its controllers (10), `MeshData` and the mesh generators (11),
`Scene` (12), materials (15), and lights (16) — and `pf::usd_import` fills a
`Scene` from a USD file (13-14).

### One 3D frame, in order

From the top of the main loop to the present, with every pass the late
chapters add. No demo runs all of it — the USD viewer, the grass, and the sea
each run a different subset — but every demo keeps this order, except that
steps 7-9 do not depend on one another and demos order them differently.

```text
On the CPU, in main (07, 09)
 1. poll events; begin the ImGui frame; draw the engine's panels and pickers
 2. switch demo or sample count, if asked (09, 18): Teardown, Setup
 3. demo.Update: events, the camera, the demo's panels

VulkanRenderer::drawFrame (04)
 4. wait for this slot's fence; acquire a swapchain image; reset the fence and the slot's command pool

demo.Record — outside any rendering scope first (09)
 5. read back what this slot copied and timed last time; reset its queries         20 §9, 21 §8
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
12. hand the scene target back, written and in SHADER_READ_ONLY_OPTIMAL           08 §4, 09
13. the grass only: reduce this frame's depth into the pyramid next frame tests   26 §9

VulkanRenderer::recordFrame, the engine's part (05, 08)
14. the swapchain image: UNDEFINED → COLOR_ATTACHMENT_OPTIMAL, after the acquire
15. composite: exposure, tone curve, sRGB encode, one full-screen triangle         08, 16
16. ImGui on top                                                                   07
17. → PRESENT_SRC_KHR

drawFrame again
18. submit: wait on imageAvailable at COLOR_ATTACHMENT_OUTPUT; signal the image's renderFinished and the slot's fence
19. present; recreate the swapchain if it is out of date or the window was resized   03 §7
```

### `FrameData`, whole

Set 0, binding 0, written by every 3D demo once per frame. It grew in five
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
};

#ifdef __cplusplus
    static_assert(sizeof(FrameData) == 368, "FrameData layout drifted.");
    static_assert(offsetof(FrameData, cameraPosition) == 192, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, time) == 208, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, sunDirection) == 224, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, brdf) == 272, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, inverseViewProjection) == 288, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, ambientMode) == 352, "FrameData alignment drifted.");
#endif
```

| Fields | Added in | Read by |
| --- | --- | --- |
| `view`, `projection`, `viewProjection`, `cameraPosition` | 10 | Every 3D vertex shader, and the shading that needs the eye |
| `time`, `deltaTime` | 10 | No shader: the passes that animate (particles, grass, sea) carry their own time in their own parameter blocks |
| `sunDirection`, `sunColor`, `ambientColor` | 11 | The mesh shaders of 11 and 15. From 16 the light buffer replaces them; Meshes, the scene graph, and the USD viewer still fill them, to build their sun's light from the panel |
| `brdf` | 15 | The mesh, G-buffer, and deferred lighting shaders |
| `inverseViewProjection` | 22 | The deferred lighting pass |
| `ambientMode` | 24 | The mesh and G-buffer shaders, and the grass's ground and blades (25 §8) |

So 88 of the 368 bytes carry nothing a shader reads: 32 of padding; the 8 of
`time` and `deltaTime`, kept for the first shader that animates by them; and the
48 of the three fields Chapter 16 retired. The append-only rule keeps the last
three, because removing a field moves every field after it; doing it once, on
purpose, with every shader that includes the block rebuilt, is a cleanup the
book leaves for you.

### Named, not built

Every chapter that stops short of something says so where it stops. Here they
are in one place, grouped, each with the chapter or section it belongs to.

**The engine's two seams.** Both are places where the book wrote a pattern more
than twice without making it shared, and both are worth doing before you add
an engine-wide feature of your own.

- **The 3D demos' shared per-frame code.** Cubes, Meshes, the scene graph, the
  USD viewer, the particles, the grass, and the sea each fill `FrameData` from
  their camera by hand, pass the same `SkyInputs` to `Sky::Update`, and (in
  five of them) turn two panel angles into the sun's direction. That is why
  Chapters 16, 23, 24, and 28 each edit every demo. The rule is to share a
  pattern at its third use, which was Chapter 12: a `SunControls` beside
  `CameraControls` (two angles to a direction and an irradiance, and its panel
  section), and one function that fills `FrameData` from a camera, its
  transform, and the time.
- **Set 0 out of `SceneRenderer`.** Cubes, the particles, the ocean, and the sea
  own a whole `SceneRenderer` only for its set 0, and so build a 2048² shadow map
  with four layers, the material resources, and the mesh pipelines they never
  use. A small class of its own — the set 0 layout, the frame and light
  buffers, and the binding writes — that `SceneRenderer` owns and those four
  demos own alone would let a demo that needs only a camera build only that.

**Smaller things in the engine.**

- `FrameData`'s three retired fields (above).
- The sky's light in every lit demo: Meshes, the scene graph, the USD viewer,
  and the grass (25 §8) read `ambientMode`; the sea's rock and boat keep a flat
  ambient (31, 32), and the cubes and the particles' ground are unlit.
- The sea's rock and boat through `SceneRenderer`: they are drawn by a shader of
  their own, so they get no materials, shadows, or sky light, and the water
  gets no shadow from the boat (31, 32).
- A third particle system — rain on the sea, smoke from the boat — is the time
  to move `SprayParticles` into `VulkanGraphics` as `GpuParticles` (31).
- Shader hot reload, and the deletion queue it needs (06 §8): with sliders
  already in place, it closes the iteration loop, and it is the single most
  useful addition.
- A render graph (29 §12; ROADMAP defers it), once the demos have shown what
  passes need.
- A per-node "something below me changed" flag, so the transform update skips
  still subtrees (12 §4).
- Object names and command-buffer labels from `VK_EXT_debug_utils`, which the
  engine and its listings leave out by design (34 §7).

**Rendering.**

- Temporal anti-aliasing (18 §9; named again in 17 §13, 22, and 27): shading
  aliasing and the grass's sub-pixel blades, which MSAA cannot fix.
- Transparency: sorted, in its own pass, or order-independent (15 §12).
- Many lights: tiled or clustered light lists for forward shading (16 §5);
  Forward+ (22 §1); 2.5D culling and clustered shading (22 §8).
- Shadows for spot, point, and area lights, and many shadowed lights (17 §14);
  soft shadows that widen with distance, PCSS (17 §8); a dithered cascade blend
  (17 §13).
- Energy lost to single-bounce GGX on rough metals, compensated (24 §8); the
  clouds in the sky's light (24 §9).
- Reverse-Z (10 §2, an aside).
- `drawIndirectCount`, once something culls whole objects on the GPU (19 §7).
- A second occlusion pass against this frame's depth (26 §9).
- Soft particles (21 §10, an exercise the chapter specifies).
- Many emitters counted on the GPU, emitter shapes (sphere, box, disc, a mesh's
  surface), bursts, sub-emitters, and color over life as a ramp: sketched in
  21's "Where to go from here" and left to you.

**The grass, the clouds, and the sea.**

- Short grass folded into two blades; screen-space shadows between blades; the
  blade's color, and its roughness, as a painted ramp (27).
- Clouds you can fly through, marched on screen with temporal reprojection; a
  round planet; cloud shadows on the ground; curl noise (28).
- A faster FFT, in shared memory or with subgroup shuffles (29 §12).
- Mipmaps for the small cascades; a denser grid near the camera; better foam;
  shallow water (30 §11).
- Waves that know the rock is there; spray that lands as foam (31). A wake that
  follows the boat anywhere; the wake as waves; a boat steered from the CPU (32).

**The path tracer.**

- A whole USD scene: a BLAS per mesh, its materials and textures (33 §6).
- Next-event estimation, low-discrepancy samples, a glossy BRDF with its own
  pdf, and wavefront path tracing (33 §8).
- Ray tracing pipelines, route C (33 §7).

**Vulkan you have not used yet.** Timeline semaphores (04 §3, 29 §12); async
compute on a second queue, with ownership transfers; `VK_EXT_shader_object`;
graphics pipeline libraries; mesh shaders; `VK_EXT_descriptor_buffer`;
descriptor indexing. And Slang, when a material system starts wanting generics.

USD composition (13 §11) and subdivision surfaces (14) are not on the list on
purpose: the importer reads one file as Blender writes it, and says so in the
log when a file asks for more.

# PillowFort

A small Vulkan engine built to relearn modern Vulkan and to host graphics demos.

The engine exists to serve the demos. When the choice is between better engine
architecture and reaching the next demo sooner, pick the demo.

*This file replaces the earlier split between `ROADMAP.md` and `plan.md`. It is
the only status tracker; a checked box means the work is in the current
checkout and its exit check passes.*

## Goals

- Relearn Vulkan 1.3 with dynamic rendering and synchronization 2.
- Keep clean clone to running executable at three commands.
- Make a new demo cheap: one folder, one class, one line to register it.

## Non-goals

No asset pipeline, general-purpose editor, physics engine, audio, scripting,
networking, or shipping game. Concretely: no cooking or conversion step (models
in other formats are converted to USD in Blender before use). Scene documents
with typed editable properties, edited through the ImGui inspector and saved
and loaded by the viewer, are in scope: Gary defined scene reflection that way
on 2026-10-25, for the reference project, and Chapter 45 teaches it.
(Corrected 2026-11-25: until then this paragraph said that nothing the engine
edits is ever saved.)

A **scene graph is in scope** (decided October 2026, reversing the earlier
non-goal): an engine-owned node tree with a transform hierarchy, which USD
files import into and ImGui edits live. USD types never leave the importer.

No backend-independent graphics abstraction. There is exactly one backend and
the point is to see it clearly. Demo code may call Vulkan directly.

## Stack

| Area | Choice |
| --- | --- |
| Host | Windows x64 |
| Compiler | MSVC, C++20 |
| Project generation | Premake 5, vendored at `Vendor/premake5/` |
| Graphics | Vulkan 1.3, dynamic rendering, synchronization 2 |
| Window and input | GLFW 3.4 (submodule) |
| Debug UI | Dear ImGui, docking branch (submodule) |
| Scenes | USD via TinyUSDZ (submodule, built by premake), from step 14. No Assimp: other formats go through Blender. |
| Shaders | GLSL compiled to SPIR-V with `glslc` |
| Frames in flight | 2 |
| Configurations | Debug, Release, Dist |

The Vulkan SDK is a machine prerequisite; `premake5.lua` fails fast when
`VULKAN_SDK` is unset. GLFW and ImGui are pinned submodules built from source.

## Layout

```text
PillowFort/
├── premake5.lua              Build definition. The only place build settings live.
├── GenerateProjects.bat      Runs premake.
├── Source/
│   ├── PillowFort/           Engine static library
│   │   └── ErrorReporting/
│   └── SandboxGame/          Executable. Owns main().
├── Shaders/
├── Vendor/                   GLFW, ImGui, premake5.exe
├── docs/Tutorial/            Vulkan walkthrough and bounded project lessons (reference)
└── Build/                    Generated. Disposable. Git-ignored.
```

One folder per module under `Source/PillowFort/`. Headers sit beside their
implementation. Includes are rooted at `Source/`:

```cpp
#include "PillowFort/ErrorReporting/Log.h"
```

## Building

```bash
git submodule update --init --recursive
```

```bash
./GenerateProjects.bat
```

Then open `Build/Projects/PillowFort.sln`, pick Debug or Release, and build.

Premake expands the `**.cpp` globs **at generation time** and writes a fixed
file list into each `.vcxproj`. Adding, renaming, moving, or deleting a source
file means rerunning `GenerateProjects.bat`. Editing an existing file does not.

Do not add files or change settings from inside Visual Studio; everything under
`Build/` is regenerated output. Source files go on disk, settings go in
`premake5.lua`.

## Status

Done:

- [x] `.gitignore`, `.gitattributes`, MIT license.
- [x] Premake vendored; GLFW 3.4 and ImGui docking pinned as submodules.
- [x] `premake5.lua` defines GLFW, ImGui, `PillowFortEngine`, and `SandboxGame`.
- [x] GLFW and ImGui compile to static libraries.
- [x] `ErrorReporting/Log.h` and `Log.cpp`.
- [x] Step 1 — `SandboxGame.exe` links and runs in Debug and Release.

Current step is **2 — Window and frame loop**.

## Steps

Each step ends in something runnable. Do not start one before the previous exit
check passes. The reference column points at the tutorial chapter covering the
Vulkan theory.

| # | Step | Reference |
| --- | --- | --- |
| 1 | Make the build link | 01 |
| 2 | Window and frame loop | — |
| 3 | Instance, device, queues | 02 |
| 4 | Swapchain | 03 |
| 5 | Commands and synchronization | 04 |
| 6 | Clear frame | 05 |
| 7 | Shaders and the triangle | 06 |
| 8 | ImGui panels | 07 |
| 9 | Resources, offscreen target, composite | 08 |
| 10 | Demo harness | 09 |
| 11 | Camera and depth | 10 |
| 12 | Meshes | 11 |
| 13 | Scene graph | 12 |
| 14 | TinyUSDZ | 13 |
| 15 | USD scene import | 14 |
| 16 | Materials and textures | 15 |
| 17 | Lights | 16 |
| 18 | Shadows | 17 |
| 19 | Anti-aliasing | 18 |
| 20 | Instancing and indirect draws | 19 |
| 21+ | Demos | 20-33, 35-43 and 45-58, and the settings lesson (44 planned) |

Chapter 34 (debugging) is reference material throughout. Steps 9 and 10 were
swapped in October 2026 so that step order matches reading order: chapter 08
keeps the triangle on the renderer, and chapter 09's harness then moves it into
a demo.

### 1. Make the build link

- [x] Add `Source/SandboxGame/Main.cpp` with the only `main()`.
- [x] Call `Log::info` from it, crossing the static library boundary.
- [x] Regenerate, then build and run Debug and Release.

**Exit:** `SandboxGame.exe` runs and prints from `Log`. Done — Debug prints the
`LOG_DEBUG` line, Release compiles it out.

### 2. Window and frame loop

- [ ] Add `Source/PillowFort/Window/`.
- [ ] Create a GLFW window with `GLFW_NO_API`.
- [ ] Own every GLFW callback here; queue close, resize, key, and mouse events.
- [ ] Add a frame loop driven by `std::chrono::steady_clock` that drains the
      queue once per frame.
- [ ] Wait for events instead of spinning while the framebuffer is zero-sized.

**Exit:** the window opens, reports input and resize, minimizes without burning
CPU, restores, and closes cleanly.

### 3. Instance, device, queues

- [ ] Add `Source/PillowFort/VulkanGraphics/`.
- [ ] Create the instance; enable validation and the debug messenger in Debug.
- [ ] Take required instance extensions from GLFW.
- [ ] Create the surface.
- [ ] Pick a Vulkan 1.3 device with presentation, swapchain, dynamic rendering,
      and synchronization 2.
- [ ] Create the logical device and one graphics/present queue.

**Exit:** startup prints the selected GPU, shutdown reports no validation errors
and no leaked objects.

### 4. Swapchain

- [ ] Create the swapchain and image views.
- [ ] Prefer an SRGB surface format; use FIFO present mode.
- [ ] Recreate on resize and on out-of-date results, waiting for a nonzero
      framebuffer first.

**Exit:** repeated resize, minimize, restore, and monitor changes stay
validation-clean.

### 5. Commands and synchronization

- [ ] Create command pools and per-frame command buffers.
- [ ] Create acquire and present semaphores plus one fence per frame in flight.
- [ ] Establish the two-frames-in-flight acquire, record, submit, present cycle.

**Exit:** frames cycle without validation errors or deadlocks.

### 6. Clear frame

- [ ] Record a dynamic-rendering clear and present it.
- [ ] Verify teardown order: ImGui, then Vulkan objects, then surface, then
      window.

**Exit:** a clear color renders and survives the resize stress from step 4.

### 7. Shaders and the triangle

- [ ] Add `Shaders/Triangle/Triangle.vert.glsl` and `Triangle.frag.glsl`.
- [ ] Compile with `glslc` for Vulkan 1.3 through tracked Premake custom-build rules.
- [ ] Write SPIR-V beside the executable and resolve it relative to the
      executable, never the working directory.
- [ ] Create shader modules, pipeline layout, and graphics pipeline.
- [ ] Generate vertex positions from `gl_VertexIndex`.

No vertex buffers, descriptor sets, or camera data yet.

**Exit:** the triangle renders and survives swapchain recreation.

### 8. ImGui panels

- [ ] Add `Source/PillowFort/DebugPanels/`.
- [ ] Initialize the GLFW backend without letting it install callbacks; forward
      input from `Window`.
- [ ] Shut ImGui down before Vulkan.
- [ ] Show frame time, FPS, GPU name, and swapchain extent.

**Exit:** panels are interactive over the triangle and break neither input,
resize, nor shutdown.

### 9. Resources, offscreen target, composite

- [ ] Buffers and images allocated through VMA, after reading the
      hand-rolled version once.
- [ ] Render the scene to an `R16G16B16A16_SFLOAT` target; composite it to a
      UNORM swapchain as the frame's only sRGB encode.
- [ ] Push-constant parameters edited from ImGui; the composite samples the
      scene target through a descriptor set.

**Exit:** the triangle looks as it did in step 7, ImGui is no longer washed out,
and resizing rebuilds the offscreen target.

### 10. Demo harness

This is the step the rest of the project exists for.

- [ ] Add `Source/PillowFort/Demos/` with a `Demo` interface: setup, update,
      record, resize, teardown. `resize` rebuilds a demo's own window-sized
      images after the engine rebuilds its targets; a demo whose `resize`
      fails is detached, and the program keeps running.
- [ ] Move the triangle behind it as the first demo.
- [ ] Let `SandboxGame` list demos and switch between them from an ImGui panel.
- [ ] Give each demo its own folder and its own shaders.

**Exit:** the triangle runs as a registered demo, and adding a second demo
touches only its own folder plus one registration line.

### 11. Camera and depth

- [ ] A camera as projection parameters plus a transform, with fly and orbit
      controllers fed by `Window` events that ImGui did not capture.
- [ ] A per-frame camera uniform buffer, one per frame in flight.
- [ ] A depth buffer beside the scene target, rebuilt on resize.

**Exit:** a field of cubes can be flown through and orbited, near cubes hide far
ones, and resizing stays validation-clean.

### 12. Meshes

- [ ] Vertex input state, an interleaved vertex format, and index buffers.
- [ ] CPU mesh data uploaded through staging into device-local buffers.
- [ ] Per-draw transforms by push constant; one directional light.

**Exit:** procedural cube, sphere, and plane meshes render lit, with back faces
culled and correct winding.

### 13. Scene graph

- [ ] `Source/PillowFort/Scene/`: nodes with local transforms, parents, and
      children; world transforms updated top-down from dirty flags.
- [ ] Meshes, cameras, and (from step 17) lights are referenced from nodes.
- [ ] The renderer consumes a flat draw list built from the graph each frame.
- [ ] An ImGui hierarchy and inspector edit the running scene.

**Exit:** moving a parent moves its children; the active camera can be any
camera node; edits in the inspector show immediately.

### 14. TinyUSDZ

- [ ] Add TinyUSDZ as a pinned submodule with its own premake project.
- [ ] Update `THIRD_PARTY_NOTICES.md`.
- [ ] Load a `.usda` file and log its prim hierarchy.

**Exit:** a clean clone still builds in three commands, and the test scene's
prim tree prints.

### 15. USD scene import

- [ ] `Source/PillowFort/UsdImport/` is the only code that includes TinyUSDZ.
- [ ] Import transforms, meshes (triangulated), and cameras into the scene
      graph, honoring the stage's up axis, units, and winding.

**Exit:** the committed test scene and a Blender-exported scene both render with
correct scale, orientation, and facing.

### 16. Materials and textures

- [ ] `UsdPreviewSurface` imported as a material; one descriptor set per
      material.
- [ ] Textures uploaded with mipmaps, color textures `_SRGB`, data textures
      `UNORM`.

**Exit:** a textured scene matches its Blender viewport render in color and
roughness response.

### 17. Lights

- [ ] UsdLux distant, sphere, and rect lights imported as scene nodes.
- [ ] Lights in a per-frame buffer; forward shading loops over them.
- [ ] Exposure and a tone curve in the composite pass.

**Exit:** each light type moves and recolors from the inspector, and a
Blender-exported light rig renders without clipping.

### 18. Shadows

- [ ] A shadow map for the sun, with depth bias and filtering.
- [ ] Cascaded shadow maps covering the camera's view distance.

**Exit:** shadows are stable while the camera moves, with no acne and no
visible cascade seams.

### 19. Anti-aliasing

- [ ] Multisampled color and depth, resolved into the single-sample scene
      target with dynamic rendering's resolve attachments.
- [ ] Alpha-to-coverage for cutout materials.

**Exit:** geometric edges are smooth at 4x MSAA, and cutout edges stop
stair-stepping.

### 20. Instancing and indirect draws

- [ ] Per-instance data in a storage buffer indexed by `gl_InstanceIndex`.
- [ ] USD instances and point instancers draw as instanced meshes.
- [ ] Draws issued from an indirect buffer.

**Exit:** thousands of instances of one mesh draw in one call.

### 21+. Demos

Add them in whatever order stays interesting; each is a folder under
`Source/PillowFort/Demos/`:

- [ ] Compute fundamentals exercise (chapter 20).
- [ ] GPU particles (chapter 21).
- [ ] Deferred shading beside forward, with a live switch in the USD viewer
      (chapter 22; an engine feature, no demo folder of its own).
- [ ] A sky every 3D demo can switch on (chapter 23; an engine feature).
- [ ] Image-based lighting: the sky lights the scene, diffuse and specular,
      for each BRDF (chapter 24; an engine feature).
- [ ] Grass, toward Ghost of Tsushima (chapters 25-27).
- [ ] Volumetric clouds in that sky (chapter 28).
- [ ] FFT ocean via compute shaders (chapter 29).
- [ ] A rougher sea: cascades, JONSWAP and swell, lingering foam, sky and
      clouds in the water (chapter 30).
- [ ] Spray: GPU-decided spray at a rock, a local foam map (chapter 31).
- [ ] A boat: floating, steered, moved on the GPU, with a wake (chapter 32).
- [ ] Path tracer (chapter 33).
- [ ] The far view: one Horizon demo that sees to the horizon, with a 200 km
      lens and depth reversed inside it, terrain in rings and a flat sea, objects
      by level of detail, ground materials, plants, forests as billboards, grass,
      and one wind, then waves to the shore, surf and sand, and the world as a
      scene graph (chapters 35-45).
- [ ] Shaping a particle effect: births on a shape, an effect clock with
      bursts, prewarm, and colour, glow and size curves baked into one image
      that the vertex stage reads, rewritten inside the frame (chapter 54; the
      Particles demo grows). Chapter 55 is written: covering smoke, the GPU sort
      that draws it back to front, and flipbook smoke; other facing modes are a
      lab on the labs page.

**Where the book ends** (decided 2026-11-16). The approved queue is the end of
the guide: Chapter 53 Rolling Wind, the fix for the ball's impostor pop in the
grass, the particle chapters 54-55, the reflection lesson, Chapter 56
Everything Bends, and Chapter 58 Grass to the Horizon (long-range grass: the cards run on past the 42 m reach and fade into
the ground shaded as the same grass; one typed chapter; Gary, 2026-11-22, "Yes add it", scope "Middle: one chapter", order
"Before the editor pass"); it is written (2026-11-27), the cards running on to 120 m and fading over their last 30 m
into a canopy the ground draws, a reach that stays provisional until the laptop session. After those comes one editor
pass over the whole guide (Gary,
2026-11-20, "Yes, write them first", to "Write the reflection lesson and
Chapter 56 before the editor pass?"), and then the guide takes fixes only: no
new chapters and no new features. A chapter the guide names as planned but this queue does not
list (Chapter 44 Surf and Sand) stays planned and keeps its number, outside the
queue: the book ends without it. So does the sea amendment to Chapter 30 (its
look and the sea-state presets, designed on 2026-10-13 and not built; Gary,
2026-11-24, "Planned, outside the queue (Recommended)"): it keeps its design
notes and the label planned, and nobody proposes building it. Each new
chapter's header names the Vulkan or GPU idea it teaches.

**After Chapter 58** (Gary, 2026-11-24, "One session after Ch 58
(Recommended)"): one attended session on the RTX 4060 Laptop works through the
checks owed to it, listed once in `reference-main`'s `REFERENCE.md` ("Owed: the
RTX 4060 Laptop session").

**The queue amended** (Gary, 2026-11-18). Two additions, from a pick of four:
"The Frame, Declared (Recommended)" and "Read a SPIR-V module (Recommended)";
and, for the reflection lesson, "Yes, make it the settings rewrite
(Recommended)". In reading order the queue is now: Chapters 54 and 55, written
by hand without any pass layer; Chapter 57, The Frame, Declared, read after 55
and written after 55 landed (2026-11-19), in which the passes of Life, then of
Particles, declare what they read and write and a small layer records the
barriers, with a print that shows each derived barrier as the call the reader
would have typed (the reference keeps the hand-written route as its default);
the reflection lesson, in which the six-place settings become rows (Chapter
53's wind settings, then the particle settings), the reader then reads one
SPIR-V module with `spirv-dis`, and a small hand-written walker, an exercise and not a part (Gary, 2026-11-20, "Drop
Part 3 (Recommended)"; on 2026-11-18 he had taken it as an optional part, "Seems like a might as well?"), compares
what a shader declares (sets, bindings, kinds, stages, block offsets, the push-constant range)
with the hand-written layout when a pipeline is created, a check and not a generator; and Chapter
56, Everything Bends, which adds its settings as rows. Then Chapter 58, Grass to the Horizon (written 2026-11-27), then
the laptop session, then the whole-guide editor pass, then fixes only. Chapter
44 stays planned outside the
queue. An optional chapter on shader variants and reload was offered and not
picked.

(2026-11-21) The reflection lesson is written as `docs/Tutorial/SettingsAsRows.md`, "Settings as Rows, and What a
Shader Declares", in two parts: Gary dropped the walker as a part (2026-11-20), and it is an exercise in section 7.
Its rows cover the grass's wind and every particle setting but the preset's index. Chapter 56 followed it
(written 2026-11-23), then Chapter 58, Grass to the Horizon (written 2026-11-27); the laptop session is next, then
the whole-guide editor pass.

## Conventions

- `SandboxGame` owns the only `main()` and constructs everything explicitly.
  No singletons, service locators, static registration, or generated entry
  points.
- Constructors do not perform fallible GPU initialization. Initialization
  returns a descriptive result.
- Assertions are for programmer mistakes. Missing files, unsupported hardware,
  and initialization failures are reported, not asserted.
- Exceptions are not used for ordinary control flow.
- Name a module for the work it does, not its architectural position.
- Backend-specific types carry their backend in the name: `GlfwWindow`,
  `VulkanDevice`.
- Debug defines `PF_DEBUG`; MSVC's `/MDd` also defines `_DEBUG`. **`PF_DEBUG`
  is the rule** for the engine's own debug code and for the guide (Gary,
  2026-11-24, "PF_DEBUG, exceptions named (Recommended)"). Two files keep
  `_DEBUG` as named exceptions: `Log.h` and `SandboxGame`'s `Main.cpp`. No
  existing code is changed for it. (Until then this line said "Pick one and
  stay with it".)

## Guardrails

1. Finish a vertical slice before generalizing it.
2. Write a pattern twice before automating it.
3. Premake is authoritative for compiling and linking. Edit `premake5.lua`,
   never a generated `.vcxproj`.
4. `Build/` is disposable. Deleting it and regenerating must always work.
5. Add a dependency only when it removes work that is not part of the goal.

## Deferred

Parked deliberately. Listed so they stop reappearing as open questions.

| Parked | Why |
| --- | --- |
| Python build layer (`Tools/`) | Dropped. It was 208 lines of TODO stubs gating five former steps, and premake's globs already handle source discovery. Revisit only if premake genuinely cannot do something. |
| `PillowFort.toml` module manifest | Dropped with the Python layer, which was its only consumer. Five of its six modules had no directory on disk. |
| `PillowFortTests` project | Not in `premake5.lua`; a stale `.vcxproj` still sits in `Build/Projects/`. Re-add when there is headless logic worth testing. |
| Backend-independent `GraphicsCommands` | One backend, and hiding Vulkan defeats the purpose. |
| Schema-driven C++/GLSL codegen | Not in the queue: the queue ("Where the book ends", above) ends the book with the editor pass, then fixes only. It waited for a real camera uniform, which came in Chapter 10; the layouts it would have generated are one shared header of C++ and GLSL twins whose offsets `static_assert`s pin (`Shaders/Include/SharedShaderTypes.h`, Chapter 8, section 8). The settings lesson's walker exercise checks what a shader declares against the hand-written layout; it generates nothing. Chapter 6, section 8 still names generating pipeline layouts from SPIR-V reflection as automation a reader may consider later; the reference does not build it. |
| Render graph, shader hot reload, timeline semaphores, multiple queues, multiple windows | Not needed to run demos. |
| Assimp | USD is the one scene format; Blender converts everything else. Revisit only if conversion becomes the bottleneck. |
| Full editor workflows | Scene documents and typed properties are in scope (Gary, 2026-10-25; Chapter 45); persistent cross-document IDs, undo/redo and procedural-world authoring remain later work. (Corrected 2026-11-25: this row was "Saving scenes, reflection", parked while the scene graph was edited in memory only.) |
| Floating origin | The Horizon demo keeps the camera within 5 km of the origin, where float32 positions are still precise (chapter 35 section 4). Needed once the camera travels further. |
| Engine-wide reversed depth | The depth contract stays standard-Z (`D32_SFLOAT`, cleared to 1.0, `LESS`). Reversed depth lives inside the Horizon demo (chapter 35 section 8 lists what an engine-wide change would touch). |

`THIRD_PARTY_NOTICES.md` covers GLFW, ImGui, and premake. Update it whenever a
redistributed dependency is added — TinyUSDZ at step 14.

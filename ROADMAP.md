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

No asset pipeline, editor, physics engine, audio, scripting, networking, or shipping
game. Concretely: no cooking or conversion step (models in other formats are
converted to USD in Blender before use), and nothing the engine edits is ever
saved — the ImGui inspector changes a running scene only.

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
├── docs/Tutorial/            34-chapter Vulkan walkthrough (reference)
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
| 21+ | Demos | 20-33 |

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
- [ ] Compile with `glslc` for Vulkan 1.3 as a premake prebuild step.
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
- Debug defines `PF_DEBUG`; MSVC's `/MDd` also defines `_DEBUG`. `Log.h`
  currently uses `_DEBUG`, which works. Pick one and stay with it.

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
| Schema-driven C++/GLSL codegen | Wait for a real camera uniform or push constant. |
| Render graph, shader hot reload, timeline semaphores, multiple queues, multiple windows | Not needed to run demos. |
| Assimp | USD is the one scene format; Blender converts everything else. Revisit only if conversion becomes the bottleneck. |
| Saving scenes, reflection | The scene graph is edited in memory only. Reflection would earn its place only alongside saving. |

`THIRD_PARTY_NOTICES.md` covers GLFW, ImGui, and premake. Update it whenever a
redistributed dependency is added — TinyUSDZ at step 14.

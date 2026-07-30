# PillowFort Engine Foundation Roadmap

> Build a small C++ engine foundation with Premake, Vulkan, GLFW, and Dear
> ImGui. Add automation only after the engine exposes a repeated problem worth
> automating.

## Foundation target

The foundation is complete when `SandboxGame` can:

- build in Debug and Release from a Premake-generated Visual Studio solution;
- open a window and process keyboard, mouse, resize, and close events;
- render a procedural Vulkan triangle;
- display ImGui development panels; and
- resize, minimize, restore, and shut down without Vulkan validation errors.

Assets, scenes, gameplay architecture, physics, audio, scripting, a full
editor, reflection, and generalized code generation are outside this
foundation.

## Fixed stack

| Area | Foundation decision |
| --- | --- |
| Host | Windows x64 |
| Compiler and language | MSVC with C++20 |
| Project generation | Premake 5 |
| Graphics | Vulkan 1.3 with dynamic rendering |
| Window and input | GLFW |
| Debug panels | Dear ImGui |
| Shaders | GLSL compiled offline with `glslc` |
| Frame model | Two frames in flight |
| Configurations | Debug and Release |
| PillowFort targets | `PillowFortEngine` and `SandboxGame` |

The Vulkan SDK is a machine prerequisite. Premake is vendored, while GLFW and
Dear ImGui are pinned Git submodules. Package managers are not required.

## Ownership boundaries

`premake5.lua` is the only build definition. It owns:

- targets and source membership;
- include paths and linked libraries;
- compiler and linker settings;
- Debug and Release behavior; and
- generated-project and build-output locations.

`GenerateProjects.bat` is only a convenient Premake invocation. It does not
contain a second representation of the project.

C++ owns runtime behavior, object lifetime, module connections, and error
handling. There is no TOML build model, generated Premake input, Python build
driver, module manifest, service locator, or generated `main()`.

Shader compilation starts as an explicit `glslc` command. Once the command has
been proven manually, Premake may invoke that same command as a build step.

## Code organization

A module is a directory named after the work its code performs. All engine
module sources are compiled into `PillowFortEngine`; modules are not DLLs,
runtime plugins, base classes, or separate configuration units.

A module name should complete:

> This code is responsible for ___.

| Module | Responsibility |
| --- | --- |
| `ErrorReporting` | Prints diagnostics and stops on broken invariants |
| `EngineLoop` | Starts, advances, and stops the application |
| `WindowInput` | Owns the GLFW window, callbacks, and queued input events |
| `VulkanGraphics` | Owns Vulkan objects and records/presents drawing work |
| `DebugPanels` | Integrates ImGui and draws development inspection panels |
| `SandboxGame` | Composes the engine objects and owns `main()` |

Names such as `Foundation`, `Common`, `Manager`, `Utilities`, and `Misc` are
avoided because they do not explain what the code does.

The first renderer is explicitly Vulkan. Do not create a backend-neutral
graphics abstraction before a real second backend or another concrete caller
requires one. `VulkanGraphics` should still expose a small C++ surface and keep
raw Vulkan ownership localized.

Headers and implementation files remain together:

```text
VulkanGraphics
├── path:      Source/PillowFort/VulkanGraphics
├── namespace: pf::vulkan_graphics
└── include:   PillowFort/VulkanGraphics/VulkanRenderer.hpp
```

## Repository layout

```text
PillowFort/
├── GenerateProjects.bat
├── premake5.lua
├── ROADMAP.md
├── plan.md
├── Source/
│   ├── PillowFort/
│   │   ├── ErrorReporting/
│   │   ├── EngineLoop/
│   │   ├── WindowInput/
│   │   ├── VulkanGraphics/
│   │   └── DebugPanels/
│   └── SandboxGame/
├── Shaders/
│   ├── Include/
│   └── Triangle/
├── Tests/
│   └── Cpp/
├── Vendor/
└── Build/
```

Module directories are added when their implementation milestone starts.
`Build/` is disposable and ignored by Git.

## Dependencies and output

PillowFort links the Windows Vulkan loader directly. GLFW and ImGui are built
from their pinned submodule revisions. Volk, VMA, GLM, image decoders, model
loaders, reflection libraries, and additional graphics backends are deferred.

Before distributing a build, add `THIRD_PARTY_NOTICES.md` and record dependency
licenses.

```text
Build/
├── Projects/
├── Intermediate/
└── Artifacts/
    ├── Debug/
    └── Release/
```

No source code may depend on the repository working directory at runtime.
Shaders and other runtime files are located relative to the executable.

## Runtime contracts

`SandboxGame` explicitly constructs and connects engine objects:

```text
SandboxGame
├── ErrorReporting
├── EngineLoop
├── WindowInput
├── VulkanGraphics
└── DebugPanels
```

Startup order is error reporting, window/input, Vulkan, debug panels, then the
engine loop. Shutdown is the reverse. ImGui stops before Vulkan, the Vulkan
surface is destroyed before its GLFW window, and GLFW terminates last.

Constructors do not perform fallible GPU initialization. Initialization reports
descriptive failures. Assertions represent programmer mistakes; missing files,
unsupported hardware, and initialization failures are ordinary reported
errors.

`WindowInput` owns GLFW callbacks and queues events. `EngineLoop` drains the
queue once per frame. ImGui does not install competing callbacks and receives
explicitly forwarded input.

A zero-sized framebuffer pauses drawing and waits for events. Swapchain
recreation waits for a nonzero framebuffer. The foundation supports one
window.

The Vulkan backend uses:

- Vulkan 1.3, dynamic rendering, synchronization 2, and the swapchain
  extension;
- one graphics/presentation queue where available;
- binary acquire and present semaphores;
- one fence per frame in flight;
- two frames in flight;
- an SRGB surface format when supported; and
- FIFO presentation initially.

Multiple windows, multiple graphics queues, dedicated transfer queues, timeline
semaphores, and a render graph are deferred.

## Shader workflow

The first shader layout is intentionally explicit:

```text
Shaders/
├── Include/
│   └── Common.glsl
└── Triangle/
    ├── Triangle.vert.glsl
    └── Triangle.frag.glsl
```

First compile both shaders manually with `glslc` for Vulkan 1.3 and load the
resulting SPIR-V by explicit executable-relative filenames. After that path
works, add the same commands to Premake.

Recompiling two small shaders is acceptable initially. Dependency scanning,
hash caches, shader catalogs, hot reload, variants, and generated binding data
are added only when their absence causes a measured problem.

## Deferred Python and metaprogramming

Python is not part of the current build or repository surface. It may return as
offline development tooling when PillowFort has a concrete metadata consumer,
such as:

- serialization;
- editor-visible properties;
- network replication; or
- shared C++/GLSL GPU layouts that have become error-prone to maintain.

Before adding it, write at least two representative cases manually and identify
the repeated inputs and outputs. If generation is justified:

- one schema must be the source of truth;
- generated output must live under `Build/`;
- behavioral C++ remains handwritten;
- generation must be deterministic and testable;
- Python must not parse arbitrary C++ using regular expressions; and
- built games must not depend on Python.

This is a decision gate, not a scheduled foundation milestone.

## Milestones

### 0 — Repository baseline

- [x] Record the foundation scope and decisions.
- [x] Add `.gitignore` and `.gitattributes`.
- [x] Add the MIT license.
- [x] Vendor Premake.
- [x] Pin GLFW and ImGui as Git submodules.
- [x] Document required local tools.
- [ ] Add `THIRD_PARTY_NOTICES.md`.

**Exit:** a fresh clone has a clear, legally reviewable starting point.

### 1 — Premake and C++ hello world

- [x] Define Debug and Release configurations.
- [x] Define `PillowFortEngine` and `SandboxGame`.
- [x] Add the project-generation batch file.
- [x] Generate a Visual Studio solution containing both targets.
- [ ] Implement `ErrorReporting`.
- [ ] Add `SandboxGame::main()`.
- [ ] Build both targets in Debug and Release.

**Exit:** `SandboxGame` calls an engine logging function and exits successfully.

### 2 — Engine loop, window, and input

- [ ] Implement `EngineLoop`.
- [ ] Integrate GLFW through Premake.
- [ ] Implement `WindowInput`.
- [ ] Handle close, resize, keyboard, and mouse events.
- [ ] Confirm minimized windows wait instead of spinning.

**Exit:** `SandboxGame` opens a window, processes events, and shuts down cleanly.

### 3 — Vulkan clear frame

- [ ] Create the Vulkan instance and Debug messenger.
- [ ] Create the surface, select a device, and create queues.
- [ ] Create the swapchain, image views, commands, and synchronization.
- [ ] Clear using dynamic rendering.
- [ ] Recreate the swapchain safely.
- [ ] Verify reverse destruction order.

**Exit:** a clear frame survives resize and minimize cycles without validation
errors.

### 4 — Shaders and procedural triangle

- [ ] Write the vertex and fragment shaders.
- [ ] Prove their `glslc` commands manually.
- [ ] Add the proven commands to Premake.
- [ ] Load SPIR-V relative to the executable.
- [ ] Create the pipeline and draw using `gl_VertexIndex`.

**Exit:** the triangle renders and survives swapchain recreation.

### 5 — ImGui debug panels

- [ ] Build the official GLFW and Vulkan backends.
- [ ] Preserve `WindowInput` callback ownership.
- [ ] Show frame time, FPS, GPU name, and swapchain extent.
- [ ] Verify keyboard and mouse forwarding.

**Exit:** interactive panels render without destabilizing input or the frame
loop.

### 6 — Reproducibility and hardening

- [ ] Stress resize, minimize, restore, and shutdown.
- [ ] Test missing shaders and unsupported hardware.
- [ ] Build both configurations from an empty `Build/`.
- [ ] Add focused C++ tests for reusable non-GPU behavior.
- [ ] Document runtime ownership and debugging procedures.

**Exit:** another developer can reproduce and understand the foundation from a
fresh clone.

## Definition of done

- [x] Premake generates the two PillowFort targets.
- [ ] Debug and Release builds succeed.
- [ ] `SandboxGame` renders a Vulkan triangle and ImGui information.
- [ ] Resize, minimize, restore, and shutdown are validation-clean.
- [ ] Build output can be deleted and reproduced.
- [ ] No current feature depends on an unneeded automation layer.

## Guardrails

1. Name code after the work it performs.
2. Finish a vertical slice before generalizing.
3. Implement a pattern twice before generating it.
4. Keep Premake as the only build definition.
5. Keep Vulkan-specific code explicit until another backend truly exists.
6. Keep generated and runtime output disposable.
7. Prefer explicit construction and ownership over registration tricks.
8. Add dependencies only when they remove work outside the learning goals.
9. Reconsider reflection only when a real metadata consumer exists.
10. Let the first real game shape the engine after the foundation.

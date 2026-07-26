# PillowFort Engine

> A small, from-scratch C++ game-engine foundation with a Vulkan renderer and a
> Python-powered development toolchain.

## Goal

Build a dependable engine kernel that can:

- generate its C++ workspace with Premake;
- automate configuration, shaders, and scaffolding with Python;
- open a window and run a clean application loop;
- render a procedural triangle with Vulkan; and
- display an interactive Dear ImGui debug layer.

This roadmap intentionally ends there. Assets, scenes, ECS, physics, scripting,
audio, and a full editor will be planned after the foundation is working.

## Working assumptions

| Area | Initial decision |
| --- | --- |
| Host platform | Windows x64 |
| Compiler | MSVC |
| Language | C++20 |
| Project generator | Premake 5 |
| Tooling language | Python 3.11+ |
| Graphics | Vulkan 1.3 with dynamic rendering |
| Windowing | GLFW |
| Debug UI | Dear ImGui |
| Shaders | GLSL compiled offline with `glslc` |
| Frame model | Two frames in flight |
| Configurations | Debug and Release |

These are foundation defaults, not permanent engine constraints.

## Ownership boundaries

### Python owns development automation

- validating the local toolchain;
- reading the project configuration;
- generating derived build configuration;
- invoking Premake and the selected build tool;
- compiling and tracking shader dependencies;
- emitting the runtime shader manifest; and
- scaffolding patterns only after they have been implemented manually once.

Python must never be required to run a built game.

### Premake owns C++ build structure

- projects and targets;
- source-file selection;
- include and library paths;
- compiler and linker options; and
- Debug and Release definitions.

Premake remains the sole C++ project generator. Python may invoke it, but must
not duplicate its project logic.

### C++ owns runtime behavior

- application and window lifecycles;
- events, timing, logging, and assertions;
- Vulkan initialization and rendering;
- resource ownership and destruction; and
- Dear ImGui integration.

## Dependency policy

Start with only:

- Vulkan SDK;
- GLFW; and
- Dear ImGui.

Premake and Python are development prerequisites rather than linked runtime
dependencies.

Do not add GLM, VMA, image decoders, model loaders, logging libraries, or
reflection libraries until a completed milestone requires them.

## Repository shape

```text
PillowFort/
├── PillowFort.toml
├── premake5.lua
├── ROADMAP.md
├── Tools/
│   ├── pf.py
│   ├── pillowfort/
│   └── Templates/
├── Engine/
│   ├── Source/
│   │   ├── Core/
│   │   ├── Platform/
│   │   ├── Renderer/Vulkan/
│   │   └── UI/
│   └── Shaders/
├── Sandbox/
│   └── Source/
├── Vendor/
└── Build/
    ├── Generated/
    ├── Projects/
    └── Shaders/
```

`Build/` is disposable and ignored by Git. Scaffolded source files are normal
project files after creation and may be edited by hand.

## Tooling contract

`Tools/pf.py` is the developer-facing entry point:

```powershell
python Tools/pf.py doctor
python Tools/pf.py generate
python Tools/pf.py build --config Debug
python Tools/pf.py shader build --config Debug
python Tools/pf.py scaffold module Renderer
```

`PillowFort.toml` is the human-edited source of truth. Python derives:

- `Build/Generated/ProjectConfig.lua` for Premake;
- `Build/Generated/BuildConfig.hpp` for C++; and
- `Build/Generated/ShaderManifest.json` for the renderer.

Machine-specific paths do not belong in `PillowFort.toml`. The `doctor`
command discovers them and reports actionable failures.

## Milestones

Complete each milestone before expanding the next one.

### 0 — Establish the baseline

- [ ] Record the assumptions and non-goals in the repository.
- [ ] Add a focused `.gitignore` for build and generated output.
- [ ] Pin each vendored dependency to a known revision.
- [ ] Document the required local tools.

**Exit:** the repository communicates exactly what is—and is not—being built.

### 1 — Build the tooling spine

- [ ] Create `PillowFort.toml`.
- [ ] Implement `pf.py doctor`.
- [ ] Validate Python, Premake, MSVC, the Vulkan SDK, and `glslc`.
- [ ] Generate the Premake and C++ configuration files.
- [ ] Generate `PillowFortEngine` and `Sandbox` projects.
- [ ] Build both Debug and Release from the Python command line.

**Exit:** a fresh machine can diagnose its setup, generate the workspace, and
build a minimal executable through one documented interface.

### 2 — Create the application shell

- [ ] Implement logging, assertions, and timing.
- [ ] Wrap GLFW in a narrow `Window` interface.
- [ ] Implement application startup, event polling, and shutdown.
- [ ] Handle close, resize, minimize, and restore events.
- [ ] Keep GLFW details out of application code.

**Exit:** Sandbox opens a window, reports lifecycle events, and exits cleanly.

### 3 — Render a Vulkan clear color

- [ ] Create the Vulkan instance and Debug messenger.
- [ ] Create the window surface.
- [ ] Select a suitable physical device and queue families.
- [ ] Create the logical device and queues.
- [ ] Create the swapchain and image views.
- [ ] Add command pools, command buffers, and per-frame synchronization.
- [ ] Clear the swapchain with dynamic rendering.
- [ ] Recreate the swapchain after resize or restore.
- [ ] Destroy every Vulkan object in a defined order.

**Exit:** the clear-color frame survives resize and minimize cycles with no
Vulkan validation errors.

### 4 — Automate shaders and draw a triangle

- [ ] Discover shader sources from the configured shader directory.
- [ ] Compile GLSL with `glslc`.
- [ ] Track includes, compiler options, and source changes.
- [ ] Rebuild only dirty shader outputs.
- [ ] Keep Debug and Release outputs separate.
- [ ] Emit a deterministic shader manifest.
- [ ] Load compiled SPIR-V through logical shader names.
- [ ] Create a graphics pipeline.
- [ ] Draw a procedural triangle with `gl_VertexIndex`.

**Exit:** editing a shader rebuilds only affected outputs, and Sandbox renders
the triangle without validation errors.

### 5 — Add the ImGui debug layer

- [ ] Integrate the official GLFW and Vulkan backends.
- [ ] Isolate ImGui behind an `ImGuiLayer`.
- [ ] Display frame time, FPS, GPU name, and swapchain extent.
- [ ] Confirm keyboard and mouse input behave correctly.
- [ ] Keep renderer code independent of individual debug panels.

**Exit:** interactive ImGui renders over the triangle without destabilizing the
frame loop.

### 6 — Harden and automate proven patterns

- [ ] Stress resize, minimize, restore, and shutdown behavior.
- [ ] Produce useful failures for missing tools and unsupported GPUs.
- [ ] Verify clean Debug and Release builds from an empty `Build/` directory.
- [ ] Confirm generated files are deterministic.
- [ ] Add scaffolding only for stable, repeated engine patterns.
- [ ] Make scaffolding preview changes and refuse accidental overwrites.
- [ ] Document the frame flow, generated files, and ownership rules.

**Exit:** another developer can reproduce the complete foundation using only
the repository documentation.

## Foundation definition of done

- [ ] `pf.py doctor` validates the development environment.
- [ ] `pf.py generate` creates the Premake workspace.
- [ ] Debug and Release build through `pf.py`.
- [ ] Shader compilation is incremental and deterministic.
- [ ] Sandbox opens a Vulkan window.
- [ ] A procedural triangle renders.
- [ ] ImGui displays live renderer information.
- [ ] Resize, minimize, restore, and shutdown are validation-clean.
- [ ] Python is absent from the runtime dependency chain.
- [ ] Generated output can be deleted and reproduced.

## Deliberately deferred

- asset database and import pipeline;
- meshes, textures, materials, and cameras;
- scenes, ECS, and serialization;
- reflection or C++ header parsing;
- editor architecture and docking;
- physics, audio, scripting, and networking;
- render graphs and multithreaded rendering; and
- additional platforms or graphics backends.

When reflection becomes necessary, use an explicit schema or a Clang-based AST
tool. Do not attempt to parse arbitrary C++ with regular expressions.

## Engineering rules

1. Finish a vertical slice before generalizing it.
2. Implement a pattern manually once before generating it.
3. Keep generated output deterministic and disposable.
4. Prefer clear ownership over wrappers for every Vulkan handle.
5. Add a dependency only when it removes work outside the engine's learning
   goals.
6. Treat validation errors as milestone blockers.
7. Let the first real game determine the next roadmap.

# PillowFort Engine Foundation Roadmap

> Build a small C++ engine foundation with a Vulkan renderer, ImGui debugging,
> Premake projects, and a Python development layer.

## Target

The foundation is complete when it can:

- validate and drive its build environment through Python;
- generate a two-target C++ workspace with Premake;
- open a window and process keyboard and mouse input;
- render a procedural Vulkan triangle;
- display ImGui debug panels; and
- resize, minimize, restore, and shut down without validation errors.

Assets, scenes, gameplay architecture, physics, audio, scripting, and a full
editor are outside this roadmap.

## Fixed stack

| Area | Foundation decision |
| --- | --- |
| Host | Windows x64 |
| Compiler and language | MSVC with C++20 |
| Project generation | Premake 5 |
| Development automation | Python 3.11+ |
| Graphics | Vulkan 1.3 with dynamic rendering |
| Window and input | GLFW |
| Debug panels | Dear ImGui |
| Shaders | GLSL compiled offline with `glslc` |
| Frame model | Two frames in flight |
| Configurations | Debug and Release |
| C++ targets | `PillowFortEngine` and `SandboxGame` |

## Code organization

A module is a build-time source and dependency group compiled into one of the
two C++ targets. It is not a DLL, runtime plugin, singleton, or C++ base class.

A module name must complete:

> This code is responsible for ___.

Names such as `Core`, `Foundation`, `Common`, `Runtime`, `Platform`, `API`,
`System`, `Manager`, `Utilities`, and `Misc` are rejected because they describe
architectural position rather than work.

| Module | Responsibility |
| --- | --- |
| `ErrorReporting` | Prints diagnostics, represents recoverable failures, and stops on broken invariants |
| `EngineLoop` | Starts and stops the application and advances it once per frame |
| `WindowInput` | Opens the window and collects window, keyboard, and mouse events |
| `GraphicsCommands` | Defines the small backend-independent drawing requests needed by the foundation |
| `VulkanGraphics` | Converts drawing requests into Vulkan work and owns Vulkan objects |
| `DebugPanels` | Integrates ImGui and draws development-only inspection panels |
| `SandboxGame` | Composes the modules into a test executable and owns `main()` |

`GraphicsCommands` stays narrow. It does not become a material system, resource
database, render graph, or universal graphics abstraction.

Names map directly:

```text
VulkanGraphics
├── path:      Source/PillowFort/VulkanGraphics
├── namespace: pf::vulkan_graphics
└── include:   PillowFort/VulkanGraphics/VulkanDevice.hpp
```

Backend-specific types include their backend, such as `GlfwWindow`,
`VulkanDevice`, and `ImGuiDebugPanels`.

## Repository layout

```text
PillowFort/
├── PillowFort.toml
├── premake5.lua
├── ROADMAP.md
├── Source/
│   ├── PillowFort/
│   │   ├── ErrorReporting/
│   │   ├── EngineLoop/
│   │   ├── WindowInput/
│   │   ├── GraphicsCommands/
│   │   ├── VulkanGraphics/
│   │   └── DebugPanels/
│   └── SandboxGame/
├── Shaders/
│   └── Include/
├── Schemas/
├── Tools/
│   ├── pillowfort.py
│   └── pillowfort_build/
├── Vendor/
└── Build/
```

Headers and implementation files remain together. Public/private source trees
are added only if PillowFort gains an external SDK or binary boundary.
`Build/` is disposable and ignored by Git.

## One handwritten configuration file

`PillowFort.toml` is the only handwritten build-information file:

```toml
[project]
name = "PillowFort"
namespace = "pf"

[graphics]
vulkan_version = "1.3"
frames_in_flight = 2

[modules]
ErrorReporting = []
EngineLoop = ["ErrorReporting"]
WindowInput = ["ErrorReporting"]
GraphicsCommands = ["ErrorReporting"]
VulkanGraphics = [
    "ErrorReporting",
    "WindowInput",
    "GraphicsCommands",
]
DebugPanels = [
    "ErrorReporting",
    "WindowInput",
    "GraphicsCommands",
    "VulkanGraphics",
]

[applications]
SandboxGame = [
    "EngineLoop",
    "WindowInput",
    "GraphicsCommands",
    "VulkanGraphics",
    "DebugPanels",
]
```

Python derives paths, namespaces, module roots, target membership, and
dependency order. Premake expands source membership from those roots. There
are no per-module manifests, handwritten shader manifests, per-target scripts,
or per-directory information files.

If this file approaches roughly 100 lines, remove redundant options before
considering nested configuration.

## Python development layer

Python is required for development but never for running a built game.

Python owns:

- environment and configuration validation;
- module dependency checks and cycle detection;
- deterministic generated build inputs;
- Premake and MSBuild invocation;
- incremental shader compilation;
- generated-file ownership and safe cleanup;
- module creation after the pattern has been proven; and
- future schema-driven C++ generation.

Premake alone owns C++ targets, source membership, compiler/linker flags,
include paths, libraries, and build configurations. C++ alone owns runtime
behavior.

The initial tooling is flat, explicit, and standard-library-only:

```text
Tools/pillowfort_build/
├── command_line.py
├── environment_check.py
├── project_configuration.py
├── module_dependencies.py
├── premake_generation.py
├── build_execution.py
├── shader_compilation.py
├── generated_file_cache.py
├── module_creation.py
└── error_messages.py
```

Files named `utils.py`, `helpers.py`, `common.py`, `model.py`, or `manager.py`
are avoided.

Paths use `pathlib`, and external programs receive argument arrays rather than
shell command strings. Paths containing spaces must work from the beginning.

### Commands

```powershell
python Tools/pillowfort.py environment check
python Tools/pillowfort.py project generate
python Tools/pillowfort.py build --configuration Debug
python Tools/pillowfort.py shader compile --configuration Debug
python Tools/pillowfort.py module graph
python Tools/pillowfort.py module create TextureLoading
python Tools/pillowfort.py configuration explain
python Tools/pillowfort.py test
```

`module create` is implemented only after two modules have been built manually.
It previews changes, refuses overwrites, and modifies only a complete assignment
inside `[modules]` or `[applications]`; it never rewrites the entire TOML file.

### Non-recursive build flow

```text
project generate
  → validate configuration
  → generate Premake inputs
  → invoke Premake

build
  → prepare generated files and shaders
  → invoke MSBuild

Visual Studio pre-build
  → prepare generated files and shaders only

shader compile
  → invoke glslc only
```

Shader compilation never invokes Premake or MSBuild. A Visual Studio build
never starts another Visual Studio build.

## Dependencies and output

The Vulkan SDK is a machine prerequisite. GLFW and Dear ImGui are pinned Git
submodules. Python validates them but never downloads or updates dependencies
during project generation.

The engine links the Windows Vulkan loader directly. Volk, VMA, GLM, image
decoders, model loaders, and reflection libraries are deferred.

Before vendoring code in the public repository, choose a project license and
add third-party notices.

```text
Build/
├── Generated/
│   ├── PremakeInputs.generated.lua
│   └── ResolvedProject.json
├── Intermediate/
│   └── PillowFortBuild/GenerationCache.json
├── Projects/
└── Artifacts/
    ├── Debug/SandboxGame/
    │   ├── SandboxGame.exe
    │   └── Shaders/
    │       ├── CompiledShaderCatalog.json
    │       └── *.spv
    └── Release/
```

Generated output is sorted, UTF-8 with LF endings, free of timestamps and
machine paths, written atomically only when changed, protected from parallel
writes, and removable only through its ownership record. A `.gitattributes`
file will enforce line endings for tracked text.

`ResolvedProject.json` is diagnostic output, not a second source of truth.

## Runtime contracts

`SandboxGame` explicitly creates and connects runtime objects. There is no
static registration, linker discovery, service locator, or generated `main()`.

```text
SandboxGame
├── EngineLoop
├── WindowInput
├── VulkanGraphics
└── DebugPanels
```

Startup is error reporting → window/input → Vulkan → debug panels → engine
loop. Shutdown is the reverse. Debug panels stop before Vulkan, and the Vulkan
surface is destroyed before the GLFW window.

Constructors do not perform fallible GPU initialization. Initialization
returns a descriptive result. Assertions represent programmer mistakes;
missing files, unsupported hardware, and initialization failures are reported
normally. Exceptions are not used for ordinary control flow or passed across
module boundaries.

`WindowInput` owns GLFW callbacks and queues events. `EngineLoop` drains the
queue once per frame. ImGui is initialized without installing competing
callbacks and receives explicitly forwarded input.

A zero-sized framebuffer pauses drawing and waits for events. Swapchain
recreation waits for a nonzero framebuffer. The foundation supports one
window.

The Vulkan backend uses:

- Vulkan 1.3, dynamic rendering, synchronization 2, and the swapchain
  extension;
- one graphics/presentation queue where available;
- binary acquire/present semaphores;
- one fence per frame in flight;
- two frames in flight;
- an SRGB surface format when supported; and
- FIFO presentation initially.

Timeline semaphores, multiple graphics queues, dedicated transfer queues,
multiple windows, and a render graph are deferred. Validation errors block
milestone completion; warnings are reviewed.

## Shader workflow

```text
Shaders/
├── Include/Common.glsl
└── Triangle/
    ├── Triangle.vert.glsl
    └── Triangle.frag.glsl
```

Python discovers known stage suffixes, invokes `glslc` for Vulkan 1.3, uses
compiler dependency files, and hashes the compiler identity, options, source,
stage, and transitive includes. Only invalid outputs are rebuilt.

SPIR-V and `CompiledShaderCatalog.json` are written beside the executable.
Runtime lookup is executable-relative, never repository-root or
working-directory-relative.

Debug shaders include debug information without optimization. Release shaders
are optimized. Hot reload, shader variants, and pipeline information files are
deferred.

## Future C++ generation

Python will replace selected reflection and template metaprogramming only when
a real consumer exists.

- Schemas define generated plain data rather than annotating duplicate C++.
- Behavioral classes remain handwritten.
- Generated declarations and metadata live under `Build/Generated`.
- Schema versions and stable field identifiers are explicit.
- Python never parses arbitrary C++ with regular expressions.

The first schema generator waits for serialization, editable properties, or
another concrete metadata consumer.

## Milestones

### 0 — Repository baseline

- [x] Record the foundation scope and decisions.
- [ ] Add `.gitignore` and `.gitattributes`.
- [ ] Choose a project license and third-party notice policy.
- [ ] Add pinned GLFW and ImGui submodules.
- [ ] Document required local tools.

**Exit:** the repository has a reproducible and legally clear starting point.

### 1 — Python build layer and Premake

- [ ] Create `PillowFort.toml`.
- [ ] Implement `environment check`.
- [ ] Validate module names, paths, dependencies, and cycles.
- [ ] Generate deterministic Premake inputs.
- [ ] Generate and build both C++ targets in Debug and Release.
- [ ] Test configuration and dependency behavior.

**Exit:** a fresh machine can diagnose, generate, and build through Python.

### 2 — Loop, errors, window, and input

- [ ] Implement `ErrorReporting`, `EngineLoop`, and `WindowInput`.
- [ ] Handle window lifecycle, keyboard, and mouse events.
- [ ] Confirm minimized windows wait instead of spinning.
- [ ] Implement `module create` from the proven module shape.

**Exit:** `SandboxGame` opens a window, processes input, and shuts down cleanly.

### 3 — Vulkan clear frame

- [ ] Implement the narrow `GraphicsCommands` contract.
- [ ] Create Vulkan instance, debugging, surface, device, and queues.
- [ ] Create swapchain, image views, commands, and synchronization.
- [ ] Clear with dynamic rendering and recreate the swapchain safely.
- [ ] Verify destruction order.

**Exit:** a clear frame survives resize/minimize cycles without validation
errors.

### 4 — Automated shaders and triangle

- [ ] Implement deterministic shader discovery and compilation.
- [ ] Track compiler-produced include dependencies.
- [ ] Cache using complete input hashes.
- [ ] Emit and load the compiled shader catalog.
- [ ] Create the pipeline and draw with `gl_VertexIndex`.

**Exit:** only affected shaders rebuild, and the triangle renders cleanly.

### 5 — ImGui debug panels

- [ ] Integrate official GLFW and Vulkan backends.
- [ ] Preserve `WindowInput` callback ownership.
- [ ] Show frame time, FPS, GPU name, and swapchain extent.
- [ ] Verify keyboard and mouse forwarding.

**Exit:** interactive debug panels render without destabilizing the frame loop.

### 6 — Reproducibility and hardening

- [ ] Stress resize, minimize, restore, and shutdown.
- [ ] Test missing tools, shaders, and unsupported GPUs.
- [ ] Build both configurations from an empty `Build/`.
- [ ] Verify deterministic generation and parallel-write locking.
- [ ] Test module-creation preview and overwrite refusal.
- [ ] Document build flow and runtime ownership.

**Exit:** another developer can reproduce and understand the foundation using
only repository documentation.

## Definition of done

- [ ] Environment failures are actionable.
- [ ] Python generates and builds the Premake workspace.
- [ ] The module graph is validated and inspectable.
- [ ] Shader compilation is incremental and deterministic.
- [ ] `SandboxGame` renders a Vulkan triangle and ImGui information.
- [ ] Resize, minimize, restore, and shutdown are validation-clean.
- [ ] Python is absent from runtime dependencies.
- [ ] Generated output can be deleted and reproduced.

## Guardrails

1. Name code after the work it performs.
2. Finish a vertical slice before generalizing.
3. Implement a pattern twice before generating it.
4. Keep one handwritten build-information file.
5. Keep Python out of the runtime dependency chain.
6. Keep Premake authoritative for C++ compilation and linking.
7. Keep generated output deterministic, inspectable, and disposable.
8. Prefer explicit ownership over registration and reflection tricks.
9. Add dependencies only when they remove work outside the learning goals.
10. Let the first real game define the roadmap after the foundation.

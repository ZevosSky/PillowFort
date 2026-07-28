# PillowFort Build Order

This file is the implementation checklist. Complete it from top to bottom and
do not begin a numbered section until the previous section's exit check passes.

Design decisions and scope live in [ROADMAP.md](ROADMAP.md).

## 1. Prepare the repository

- [ ]  Add `.gitignore` for `Build/`, generated IDE files, caches, and local
  editor files.
- [ ]  Add `.gitattributes` that treats source, shader, Python, Lua, TOML, and
  Markdown files as text with LF endings.
- [ ]  Choose and add the project license.
- [ ]  Create `THIRD_PARTY_NOTICES.md`.
- [ ]  Document the supported versions of Python, Premake, MSVC, the Windows
  SDK, and the Vulkan SDK.

**Exit check:** a fresh clone contains no machine-specific files and has an
explicit license and line-ending policy.

## 2. Verify the development machine

Install or verify:

- [ ]  Git with submodule support.
- [ ]  Python 3.11 or newer.
- [ ]  Premake 5.
- [ ]  Visual Studio with the Desktop development with C++ workload.
- [ ]  A Windows SDK.
- [ ]  A Vulkan 1.3-capable driver and GPU.
- [ ]  The Vulkan SDK, including validation layers and `glslc`.

Record how each tool is found. Machine-specific paths must come from tool
discovery or environment variables, not committed configuration.

**Exit check:** every required executable and SDK can be located from a new
PowerShell session.

## 3. Create the single project configuration

- [ ]  Add `PillowFort.toml`.
- [ ]  Define the project name, namespace, Vulkan version, and frames in flight.
- [ ]  Register only the first library module and application:

```toml
[modules]
ErrorReporting = []

[applications]
SandboxGame = ["ErrorReporting"]
```

- [ ]  Add later modules only when their implementation step begins.
- [ ]  Keep paths and namespaces derived from module names.
- [ ]  Reject per-module and per-directory configuration files.

**Exit check:** the initial dependency graph is represented in one small TOML
file with no machine paths.

## 4. Build the Python command shell

- [ ]  Add `Tools/pillowfort.py`.
- [ ]  Add the `Tools/pillowfort_build` package.
- [ ]  Implement command parsing and consistent error messages.
- [ ]  Use `pathlib` for paths.
- [ ]  Invoke external programs with argument arrays, never shell-built command
  strings.
- [ ]  Confirm repository paths containing spaces work.
- [ ]  Add the initial command:

```powershell
python Tools/pillowfort.py environment check
```

The command must verify Python, Premake, MSVC, the Windows SDK, the Vulkan SDK,
`glslc`, and required environment variables. Each failure must explain how to
fix it.

**Exit check:** `environment check` succeeds on the development machine and
produces a useful failure when any one dependency is hidden.

## 5. Create the minimal C++ source

Create these files manually:

```text
Source/
├── PillowFort/
│   └── ErrorReporting/
│       ├── Log.hpp
│       └── Log.cpp
└── SandboxGame/
    └── Main.cpp
```

- [ ]  Implement a minimal console log function.
- [ ]  Make `SandboxGame` own `main()`.
- [ ]  Call the engine log function from `main()`.
- [ ]  Do not introduce a generated entry point, singleton, or service locator.

**Exit check:** the intended dependency direction is
`SandboxGame → ErrorReporting`.

## 6. Validate modules and dependencies

- [ ]  Parse `PillowFort.toml` with `tomllib`.
- [ ]  Validate project and module names.
- [ ]  Reject module names that differ only by letter casing.
- [ ]  Confirm every dependency and source directory exists.
- [ ]  Detect dependency cycles.
- [ ]  Produce a stable topological order.
- [ ]  Implement:

```powershell
python Tools/pillowfort.py module graph
python Tools/pillowfort.py configuration explain
```

- [ ]  Test valid graphs, missing dependencies, cycles, missing directories, and
  casing collisions with `unittest`.

**Exit check:** module order is deterministic, inspectable, and covered by
tests.

## 7. Generate the Premake workspace

- [ ]  Add the handwritten `premake5.lua`.
- [ ]  Keep compiler flags, linker flags, configurations, libraries, and targets
  in Premake.
- [ ]  Make Python emit only `Build/Generated/PremakeInputs.generated.lua`.
- [ ]  Make Premake expand source membership from generated module roots.
- [ ]  Generate only:
  - `PillowFortEngine` as a static library;
  - `SandboxGame` as a console executable.
- [ ]  Implement:

```powershell
python Tools/pillowfort.py project generate
python Tools/pillowfort.py build --configuration Debug
python Tools/pillowfort.py build --configuration Release
```

- [ ]  Ensure `build` invokes generation logic directly and never recursively
  launches another build command.

**Exit check:** Debug and Release both print the engine log message from
`SandboxGame`.

## 8. Implement error reporting

- [ ]  Add Debug, Info, Warning, and Error log levels.
- [ ]  Add assertions for programmer invariants.
- [ ]  Add a descriptive initialization-result type.
- [ ]  Keep expected failures out of assertions.
- [ ]  Do not use exceptions for normal module control flow.

**Exit check:** logs identify their severity, a failed initialization carries a
message, and a deliberately broken Debug assertion stops locally.

## 9. Implement the engine loop

- [ ]  Add `EngineLoop = ["ErrorReporting"]` to `[modules]`.
- [ ]  Create `Source/PillowFort/EngineLoop`.
- [ ]  Create `EngineLoop`.
- [ ]  Use a monotonic clock for frame timing.
- [ ]  Add explicit start, frame, and stop behavior.
- [ ]  Change `SandboxGame` to depend directly on `EngineLoop`.
- [ ]  Remove the temporary direct logging call from `SandboxGame`.
- [ ]  Keep `SandboxGame` responsible for constructing dependencies.
- [ ]  Do not let `EngineLoop` create the window or renderer.

**Exit check:** `SandboxGame` advances a fixed number of test frames, reports
delta time, and stops cleanly.

## 10. Add GLFW and implement window/input

- [ ]  Add `WindowInput = ["ErrorReporting"]` to `[modules]`.
- [ ]  Create `Source/PillowFort/WindowInput`.
- [ ]  Add GLFW as a pinned Git submodule.
- [ ]  Record its license in `THIRD_PARTY_NOTICES.md`.
- [ ]  Build GLFW through Premake.
- [ ]  Create a Vulkan-compatible window with no OpenGL context.
- [ ]  Make `WindowInput` own all GLFW callbacks.
- [ ]  Queue close, resize, keyboard, and mouse events.
- [ ]  Drain the event queue once per engine frame.
- [ ]  Pause frame work and wait for events while the framebuffer is zero-sized.
- [ ]  Add `WindowInput` to the direct dependencies of `SandboxGame`.

**Exit check:** the window opens, reports input and resize events, minimizes
without busy-spinning, restores, and closes cleanly.

## 11. Automate proven module creation

`ErrorReporting`, `EngineLoop`, and `WindowInput` now provide the pattern.

- [ ]  Implement:

```powershell
python Tools/pillowfort.py module create GraphicsCommands --depends ErrorReporting
python Tools/pillowfort.py module create VulkanGraphics --depends ErrorReporting WindowInput GraphicsCommands
python Tools/pillowfort.py module create DebugPanels --depends ErrorReporting WindowInput GraphicsCommands VulkanGraphics
```

- [ ]  Preview every file and configuration change.
- [ ]  Refuse invalid names, duplicate names, and existing paths.
- [ ]  Create source directories and minimal editable files.
- [ ]  Modify only one complete entry inside `[modules]` or `[applications]`.
- [ ]  Never rewrite the entire TOML document.
- [ ]  Add dry-run and overwrite-refusal tests.
- [ ]  Use the command to create `GraphicsCommands`, `VulkanGraphics`, and
  `DebugPanels`.
- [ ]  Add all three modules to the direct dependencies of `SandboxGame`.
- [ ]  Regenerate the Premake workspace and build after creation.

**Exit check:** generated module skeletons build, and rerunning the command
cannot overwrite them.

## 12. Define the graphics boundary

- [ ]  Keep Vulkan types out of `GraphicsCommands`.
- [ ]  Define only the frame operations required by the first renderer.
- [ ]  Add a clear color and frame status.
- [ ]  Avoid materials, meshes, textures, render graphs, and resource managers.
- [ ]  Make `VulkanGraphics` implement the narrow drawing contract.

**Exit check:** `SandboxGame` can request a frame without including Vulkan
headers.

## 13. Initialize Vulkan

- [ ]  Link the Windows Vulkan loader.
- [ ]  Create the Vulkan instance.
- [ ]  Enable validation and the debug messenger in Debug.
- [ ]  Ask GLFW for required instance extensions.
- [ ]  Create the window surface.
- [ ]  Select a Vulkan 1.3 device supporting presentation, swapchains, dynamic
  rendering, and synchronization 2.
- [ ]  Create the logical device and graphics/presentation queue.
- [ ]  Add readable names to Vulkan objects in Debug.

**Exit check:** startup prints the selected GPU and exits without validation
errors or leaked Vulkan objects.

## 14. Render and present a clear frame

- [ ]  Create the swapchain and image views.
- [ ]  Prefer an SRGB surface format and use FIFO presentation.
- [ ]  Create command pools and command buffers.
- [ ]  Create acquire/present semaphores and one fence per frame in flight.
- [ ]  Record a dynamic-rendering clear operation.
- [ ]  Present the image.
- [ ]  Recreate the swapchain after resize or an out-of-date result.
- [ ]  Wait for a nonzero framebuffer before recreation.
- [ ]  Destroy Debug panels, Vulkan objects, the surface, and the window in the
  correct reverse order.

**Exit check:** the clear color survives repeated resize, minimize, restore,
and moving the window between monitors without validation errors.

## 15. Automate shader compilation

- [ ]  Add:

```text
Shaders/Triangle/Triangle.vert.glsl
Shaders/Triangle/Triangle.frag.glsl
```

- [ ]  Implement:

```powershell
python Tools/pillowfort.py shader compile --configuration Debug
```

- [ ]  Discover shader stages from explicit suffixes.
- [ ]  Compile for Vulkan 1.3 with `glslc`.
- [ ]  Use compiler dependency files for includes.
- [ ]  Hash compiler identity, options, stage, source, and transitive includes.
- [ ]  Rebuild only invalid outputs.
- [ ]  Write outputs atomically.
- [ ]  Emit `CompiledShaderCatalog.json`.
- [ ]  Place SPIR-V and the catalog beside `SandboxGame.exe`.
- [ ]  Resolve shaders relative to the executable.

**Exit check:** the first build compiles both shaders, an unchanged second build
compiles neither, and editing one shader rebuilds only the affected output.

## 16. Draw the procedural triangle

- [ ]  Load compiled SPIR-V through the shader catalog.
- [ ]  Create shader modules, pipeline layout, and graphics pipeline.
- [ ]  Generate triangle positions from `gl_VertexIndex`.
- [ ]  Record the draw between dynamic-rendering begin/end calls.
- [ ]  Recreate swapchain-dependent pipeline state when required.

Do not add vertex buffers, camera data, descriptor sets, or shared
C++/GLSL-variable generation yet.

**Exit check:** the triangle renders and survives swapchain recreation without
validation errors.

## 17. Add ImGui debug panels

- [ ]  Add Dear ImGui as a pinned Git submodule.
- [ ]  Record its license in `THIRD_PARTY_NOTICES.md`.
- [ ]  Compile the official GLFW and Vulkan backends.
- [ ]  Initialize the GLFW backend without installing callbacks.
- [ ]  Forward input from `WindowInput`.
- [ ]  Shut ImGui down before Vulkan.
- [ ]  Display frame time, FPS, GPU name, and swapchain extent.

**Exit check:** ImGui is interactive over the triangle and does not break game
input, resize, or shutdown.

## 18. Add shared C++/shader data only when needed

The procedural triangle does not need shared variables. Wait for the first
camera uniform or push constant.

When that consumer exists:

- [ ]  Add one schema that is the source of truth for descriptor numbers and
  GPU-facing data layouts.
- [ ]  Generate one C++ header and one GLSL include.
- [ ]  Use `std140` for uniform buffers and `std430` where appropriate.
- [ ]  Generate alignment, size, and offset checks.
- [ ]  Avoid C++ `bool`, pointers, and gameplay objects in GPU-facing data.
- [ ]  Use SPIR-V reflection later as validation, not as the initial source of
  truth.

**Exit check:** C++ and GLSL layouts come from one schema and are verified by
compile-time checks.

## 19. Harden the foundation

- [ ]  Run Debug with validation for an extended session.
- [ ]  Stress resize, minimize, restore, and shutdown.
- [ ]  Test missing tools, shaders, and unsupported GPU reporting.
- [ ]  Delete `Build/` and reproduce both configurations.
- [ ]  Verify generated metadata is byte-stable for identical inputs.
- [ ]  Verify parallel IDE builds cannot corrupt generated output.
- [ ]  Confirm cleanup removes only generator-owned files.
- [ ]  Run all Python tests.

```powershell
python Tools/pillowfort.py test
python Tools/pillowfort.py build --configuration Debug
python Tools/pillowfort.py build --configuration Release
```

**Exit check:** every foundation requirement in `ROADMAP.md` is satisfied and a
fresh clone can reproduce the result using documented commands.

# PillowFort Build Plan

Complete this checklist from top to bottom. Each step ends in something that
can be generated, built, run, or visibly verified.

- [ROADMAP.md](ROADMAP.md) records the stable scope and architecture choices.
- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) records reproducible setup,
  build, run, and test commands.
- This file is the only completion-status tracker. A checked repository item
  means the current checkout contains the work and its exit check passes.
  Machine prerequisites are deliberately not tracked as completed work.

## Current checkpoint

Steps 1 through 4 form the current headless vertical slice. In Debug,
`SandboxGame` traces startup, advances three frames, and traces shutdown; in
Release those trace calls compile out. `PillowFortTests` verifies the reusable
engine-loop behavior without a window or GPU. The next implementation step is
GLFW window and input integration.

## 1. Finish the repository baseline

**Learning focus:** separate source-of-truth files from disposable output, and
understand the obligations that come with redistributed dependencies.

- [x] Ignore `Build/`, IDE state, and local caches.
- [x] Enforce consistent tracked text line endings.
- [x] Add the MIT license.
- [x] Vendor Premake.
- [x] Add pinned GLFW and ImGui submodules.
- [x] Add `THIRD_PARTY_NOTICES.md` for Premake, GLFW, and ImGui.

**Exit check:** `git status --short` contains no generated build or
machine-specific files after project generation and a build.

## 2. Verify the local C++ toolchain and generate projects

Use the exact prerequisites and commands in
[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md). At this stage the required
machine tools are Git, Visual Studio 2022 with its C++ workload, MSVC with C++20
support, and a Windows SDK. Vulkan is intentionally not a prerequisite yet.

- [x] Keep Premake as the only build definition.
- [x] Generate `Build/Projects/PillowFort.sln`.
- [x] Generate the product targets `PillowFortEngine` and `SandboxGame`.
- [x] Generate the verification target `PillowFortTests`.
- [x] Expose only Debug and Release configurations for PillowFort code.

**Exit check:** deleting the disposable `Build/` directory and rerunning
`GenerateProjects.bat` reproduces the solution.

## 3. Build the first C++ vertical slice

```text
Source/
├── PillowFort/
│   └── Logging/
│       ├── Log.hpp
│       └── Log.cpp
└── SandboxGame/
    └── Main.cpp
```

**Learning focus:** keep ownership of the program entry point clear and cross a
real static-library boundary before adding engine architecture.

- [x] Add the small `pf::logging::WriteLine` console API.
- [x] Compile `PF_TRACE` calls into Debug and out of Release without evaluating
  disabled trace arguments.
- [x] Make `SandboxGame` own the only `main()`.
- [x] Call the engine reporting function from `main()`.
- [x] Build and run Debug.
- [x] Build and run Release.

Do not add a singleton logger, generated entry point, application base class,
or registration mechanism.

**Exit check:** Debug prints the lifecycle trace messages; Release returns
success without printing them.

## 4. Implement and test the engine loop

**Learning focus:** model control flow with explicit ownership and test logic at
the seam where platform and graphics code will later connect.

- [x] Create `Source/PillowFort/EngineLoop`.
- [x] Represent loop control with an explicitly owned C++ object.
- [x] Calculate frame delta and elapsed time using `std::chrono::steady_clock`.
- [x] Let the caller request shutdown.
- [x] Add a fixed-frame test that does not create a window.
- [x] Verify that one loop object can be run again after stopping.

**Exit check:** `PillowFortTests` passes, and `SandboxGame` advances exactly
three frames before exiting cleanly.

## 5. Integrate GLFW and window/input

**Learning focus:** turn callback-driven platform input into owned, ordered
events that the frame loop can consume deterministically.

- [ ] Add a Premake project or explicit source block for GLFW.
- [ ] Link GLFW into `PillowFortEngine`.
- [ ] Create `Source/PillowFort/WindowInput`.
- [ ] Open one Vulkan-compatible window with no OpenGL context.
- [ ] Make `WindowInput` own all GLFW callbacks.
- [ ] Queue close, resize, keyboard, and mouse events.
- [ ] Drain queued events once per engine frame.
- [ ] Wait for events while the framebuffer is zero-sized.
- [ ] Add CPU-only tests for event queue ordering and state transitions.

**Exit check:** the window opens, reports events, minimizes without busy
spinning, restores, and closes cleanly.

## 6. Initialize Vulkan

Before starting this step, verify a Vulkan 1.3-capable driver and GPU plus the
Vulkan SDK and validation layers. Record the actual SDK and GPU used while
learning; do not make earlier milestones depend on them.

**Learning focus:** practice explicit capability discovery and reverse-order
resource lifetime without hiding Vulkan behind a premature abstraction.

- [ ] Create `Source/PillowFort/VulkanGraphics`.
- [ ] Link the Windows Vulkan loader.
- [ ] Ask GLFW for required instance extensions.
- [ ] Create a Vulkan 1.3 instance.
- [ ] Enable validation and the Debug messenger in Debug.
- [ ] Create the GLFW window surface.
- [ ] Select a device supporting presentation, swapchains, dynamic rendering,
  and synchronization 2.
- [ ] Create the logical device and graphics/presentation queue.

Keep Vulkan handles and headers localized to `VulkanGraphics`. Do not create a
generic graphics-backend interface yet.

**Exit check:** startup reports the selected GPU and shutdown produces no
validation errors or leaked Vulkan objects.

## 7. Render and present a clear frame

**Learning focus:** understand image ownership, layout transitions,
synchronization, and why swapchains are recreated rather than resized.

- [ ] Create the swapchain and image views.
- [ ] Prefer an SRGB format and FIFO presentation.
- [ ] Create command pools and command buffers.
- [ ] Create acquire/present semaphores and one fence per frame in flight.
- [ ] Record a dynamic-rendering clear operation.
- [ ] Present the image.
- [ ] Recreate the swapchain after resize or out-of-date results.
- [ ] Wait for a nonzero framebuffer before recreating.
- [ ] Verify reverse destruction order.

**Exit check:** the clear color survives repeated resize, minimize, restore,
and monitor moves without validation errors.

## 8. Compile shaders and draw the triangle

Before starting this step, verify that the Vulkan SDK's `glslc` is available.

```text
Shaders/Triangle/Triangle.vert.glsl
Shaders/Triangle/Triangle.frag.glsl
```

**Learning focus:** prove each transformation from GLSL source to pipeline
execution before automating it.

- [ ] Compile both shaders manually with `glslc` for Vulkan 1.3.
- [ ] Put the resulting SPIR-V beside `SandboxGame.exe`.
- [ ] Load the shaders relative to the executable, not the working directory.
- [ ] Create the shader modules, pipeline layout, and graphics pipeline.
- [ ] Generate positions using `gl_VertexIndex`.
- [ ] Draw and survive swapchain recreation.
- [ ] After manual compilation works, add those exact commands to Premake.

It is acceptable to rebuild two tiny shaders. Do not add hashing, catalogs,
manifests, reflection, variants, or hot reload yet.

**Exit check:** the procedural triangle renders from both Debug and Release
output directories.

## 9. Integrate ImGui debug panels

**Learning focus:** integrate a third-party system without giving it ownership
of input or engine lifetime.

- [ ] Create `Source/PillowFort/DebugPanels`.
- [ ] Compile the official GLFW and Vulkan ImGui backends.
- [ ] Initialize the GLFW backend without installing callbacks.
- [ ] Forward input explicitly from `WindowInput`.
- [ ] Shut ImGui down before Vulkan.
- [ ] Show frame time, FPS, GPU name, and swapchain extent.

**Exit check:** ImGui is interactive over the triangle and does not break game
input, resize, or shutdown.

## 10. Harden and document the foundation

**Learning focus:** distinguish a demo that works once from a foundation that
another developer can reproduce and diagnose.

- [x] Establish a focused C++ test target for reusable non-GPU behavior.
- [ ] Add tests as new reusable CPU-only behavior appears.
- [ ] Stress resize, minimize, restore, and shutdown.
- [ ] Test missing-shader and unsupported-GPU reporting.
- [ ] Delete `Build/` and reproduce Debug and Release.
- [ ] Document runtime object ownership and Vulkan debugging procedures.
- [x] Document current setup, build, run, and test commands outside the scratch
  README.
- [x] Add third-party notices and keep distributed licenses in the repository.

**Exit check:** a fresh clone can reproduce the foundation using
`docs/GETTING_STARTED.md` and the checked-in files.

## 11. Reconsider offline automation only after a real need

This is a decision checkpoint, not current implementation work.

- [ ] Identify a concrete consumer such as serialization, editable properties,
  replication, or shared GPU layouts.
- [ ] Implement at least two representative cases manually.
- [ ] Write down exactly what is repetitive and error-prone.
- [ ] Compare explicit C++, schema-first generation, and Clang-based tooling.
- [ ] Introduce Python only if it clearly reduces total complexity.

Any future generator must keep Python out of the built game, write generated
files under `Build/`, and avoid parsing arbitrary C++ with regular
expressions.

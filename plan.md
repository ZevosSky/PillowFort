# PillowFort Build Order

Complete this checklist from top to bottom. Each step ends in something that
can be generated, built, run, or visibly verified.

Architecture and scope decisions live in [ROADMAP.md](ROADMAP.md).

## 1. Finish the repository baseline

- [x] Ignore `Build/`, IDE state, and local caches.
- [x] Enforce consistent tracked text line endings.
- [x] Add the MIT license.
- [x] Vendor Premake.
- [x] Add pinned GLFW and ImGui submodules.
- [ ] Add `THIRD_PARTY_NOTICES.md` for GLFW, ImGui, and other distributed code.

**Exit check:** `git status` contains no generated build or machine-specific
files.

## 2. Verify the local toolchain and generate projects

Install or verify:

- [ ] Visual Studio with the **Desktop development with C++** workload.
- [ ] MSVC with C++20 support.
- [ ] A Windows SDK.
- [ ] A Vulkan 1.3-capable driver and GPU.
- [ ] The Vulkan SDK, including validation layers and `glslc`.
- [ ] Initialized submodules:

```powershell
git submodule update --init --recursive
```

Generate the Visual Studio solution:

```powershell
.\GenerateProjects.bat
```

- [x] Confirm `Build/Projects/PillowFort.sln` exists.
- [x] Confirm it contains `PillowFortEngine` and `SandboxGame`.
- [x] Confirm only Debug and Release are exposed for PillowFort.

**Exit check:** deleting `Build/` and rerunning the batch file reproduces the
solution.

## 3. Build the first C++ vertical slice

Create:

```text
Source/
├── PillowFort/
│   └── ErrorReporting/
│       ├── Log.hpp
│       └── Log.cpp
└── SandboxGame/
    └── Main.cpp
```

- [ ] Add `pf::error_reporting::WriteLine`.
- [ ] Make `SandboxGame` own the only `main()`.
- [ ] Call the engine log function from `main()`.
- [ ] Build and run Debug.
- [ ] Build and run Release.

Do not add a singleton logger, generated entry point, application base class,
or registration mechanism.

**Exit check:** the executable prints one engine message and returns success.

## 4. Implement the engine loop

- [ ] Create `Source/PillowFort/EngineLoop`.
- [ ] Represent loop control with an explicitly owned C++ object.
- [ ] Calculate frame delta using `std::chrono`.
- [ ] Let the caller request shutdown.
- [ ] Test a fixed-frame run without creating a window.

**Exit check:** `SandboxGame` advances a chosen number of frames and exits
cleanly.

## 5. Integrate GLFW and window/input

- [ ] Add a Premake project or explicit source block for GLFW.
- [ ] Link GLFW into `PillowFortEngine`.
- [ ] Create `Source/PillowFort/WindowInput`.
- [ ] Open one Vulkan-compatible window with no OpenGL context.
- [ ] Make `WindowInput` own all GLFW callbacks.
- [ ] Queue close, resize, keyboard, and mouse events.
- [ ] Drain queued events once per engine frame.
- [ ] Wait for events while the framebuffer is zero-sized.

**Exit check:** the window opens, reports events, minimizes without busy
spinning, restores, and closes cleanly.

## 6. Initialize Vulkan

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
generic graphics backend interface yet.

**Exit check:** startup reports the selected GPU and shutdown produces no
validation errors or leaked Vulkan objects.

## 7. Render and present a clear frame

- [ ] Create the swapchain and image views.
- [ ] Prefer an SRGB format and FIFO presentation.
- [ ] Create command pools and command buffers.
- [ ] Create acquire/present semaphores and one fence per frame in flight.
- [ ] Record a dynamic-rendering clear operation.
- [ ] Present the image.
- [ ] Recreate the swapchain after resize or out-of-date results.
- [ ] Wait for a nonzero framebuffer before recreating.
- [ ] Verify reverse destruction order.

**Exit check:** the clear color survives repeated resize, minimize, restore, and
monitor moves without validation errors.

## 8. Compile shaders and draw the triangle

Create:

```text
Shaders/Triangle/Triangle.vert.glsl
Shaders/Triangle/Triangle.frag.glsl
```

- [ ] Compile both shaders manually with Vulkan SDK `glslc`.
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

- [ ] Create `Source/PillowFort/DebugPanels`.
- [ ] Compile the official GLFW and Vulkan ImGui backends.
- [ ] Initialize the GLFW backend without installing callbacks.
- [ ] Forward input explicitly from `WindowInput`.
- [ ] Shut ImGui down before Vulkan.
- [ ] Show frame time, FPS, GPU name, and swapchain extent.

**Exit check:** ImGui is interactive over the triangle and does not break game
input, resize, or shutdown.

## 10. Harden and document the foundation

- [ ] Add focused C++ tests for reusable logic that does not require a GPU.
- [ ] Stress resize, minimize, restore, and shutdown.
- [ ] Test missing shader and unsupported-GPU reporting.
- [ ] Delete `Build/` and reproduce Debug and Release.
- [ ] Document object ownership and Vulkan debugging procedures.
- [ ] Add third-party notices and verify distributed licenses.

**Exit check:** a fresh clone can reproduce the foundation using only
[readme.md](readme.md) and the checked-in files.

## 11. Reconsider offline automation only after a real need

This is a decision checkpoint, not current implementation work.

- [ ] Identify a concrete consumer such as serialization, editable properties,
  replication, or shared GPU layouts.
- [ ] Implement at least two representative cases manually.
- [ ] Write down exactly what is repetitive and error-prone.
- [ ] Compare explicit C++, schema-first generation, and Clang-based tooling.
- [ ] Introduce Python only if it clearly reduces total complexity.

Any future generator must keep Python out of the built game, write generated
files under `Build/`, and avoid parsing arbitrary C++ with regular expressions.

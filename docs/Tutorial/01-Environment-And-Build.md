# 01 — Environment and Build Wiring

**Goal:** a workspace that compiles, links the Vulkan loader, builds GLFW and
ImGui from the pinned submodules, and runs with validation enabled.

**ROADMAP:** step 1.

**You need:** Windows 10 or 11 (x64), Visual Studio 2022 with the "Desktop
development with C++" workload, the Vulkan SDK (1.4.357 or later), git, and a
GPU with a Vulkan 1.3 driver. The index's
[What you need](../VulkanTutorial.md#what-you-need-and-what-it-teaches) has the
details.

---

## 1. What is actually in your SDK

Your SDK lives at `%VULKAN_SDK%` — `C:\VulkanSDK\1.4.357.0` at the time of
writing, which is what this tutorial's code was checked against. It is worth
knowing what is in there,
because several things people vendor as submodules are already installed.

```text
%VULKAN_SDK%
  Bin
    glslc.exe              GLSL to SPIR-V, gcc-style CLI, emits depfiles. Use this one.
    glslangValidator.exe   The reference compiler. Older CLI, no depfiles.
    slangc.exe             Slang to SPIR-V. Generics, modules, autodiff. See below.
    dxc.exe                HLSL to SPIR-V, if you prefer HLSL.
    spirv-dis / spirv-opt / spirv-reflect-pp / spirv-cross
    vkconfig.exe           GUI for layer configuration. Read section 5.
    vkcube.exe             Your "is my driver alive" smoke test.
  Include
    vulkan/                vulkan_core.h, vulkan.h, vulkan.hpp (the C++ bindings)
    vma/vk_mem_alloc.h     Vulkan Memory Allocator, header-only
    glm/                   GLM, header-only
    Volk/volk.h, volk.c    Meta-loader
    slang/                 Slang headers
  Lib
    vulkan-1.lib           The loader import library. This is what you link.
```

Two consequences for this project:

- **VMA and GLM need no submodule.** They are headers on an include path you
  already have. See the dependency table in the
  [index](../VulkanTutorial.md).
- **Slang is available**, and this tutorial does not use it: every shader here
  is GLSL. Because both compile to SPIR-V, switching later is one changed
  prebuild command.

Verify the toolchain from a fresh PowerShell session, before anything else
depends on it:

```bash
echo $env:VULKAN_SDK; where.exe glslc; vkcube.exe
```

`vkcube` spinning is the fastest possible proof that your driver, loader, and
ICD are all wired up. (The *loader* is `vulkan-1.dll`, which every Vulkan
program calls; the *ICD*, or installable client driver, is your GPU vendor's
Vulkan driver, which the loader finds and forwards to.) If it fails, nothing
below will work and the problem is not your code.

---

## 2. Three mistakes to avoid in any premake workspace

Each of these is easy to make in a new `premake5.lua`, and each fails somewhere
other than where it was made. The workspace in section 3 avoids all three.

**a. A misspelled name is `nil`, not an error.** Lua is case-sensitive, and a
name that was never assigned reads as `nil`. A local called `vulkanSDK`, used
later as `vulkanSdk`:

```lua
includedirs
{
    vulkanSdk .. "/Include"   -- vulkanSdk is nil; the local is named vulkanSDK
}
```

stops generation with `attempt to concatenate a nil value`, at the line that
uses the name rather than the line that declared it.

**b. `libdirs` is not `links`.** `libdirs { vulkanSDK .. "/Lib" }` says where
libraries are and links none of them. Without `links { "vulkan-1" }` everything
compiles, and the link fails with a wall of
`LNK2019 unresolved external symbol vkCreateInstance`.

**c. A static library's calls resolve when the executable links.**
`PillowFortEngine` is a `StaticLib`, so the Vulkan functions it calls are looked
up only when `SandboxGame` links: the library needs the Vulkan headers, and the
executable needs the loader. Splitting the two settings between the projects
works until the next target is added. Put both in the one function every target
calls, as section 3 does.

---

## 3. The corrected workspace

**This is `premake5.lua`**, whole; it replaces the one in the repository. It
avoids the three mistakes above and adds two libraries as vendor static
libraries: **GLFW**, which opens a window and
reports keyboard and mouse input, and **Dear ImGui**, the debug-panel library
Chapter 07 sets up.

Premake in five points, enough to read the file:

- A **workspace** is the Visual Studio solution. It holds **projects**, and
  each project becomes one `.vcxproj`.
- `kind` says what a project builds: `StaticLib` is a `.lib`, `ConsoleApp` an
  `.exe` with a console window.
- `files` lists sources, and `**` matches any number of folders deep.
- `filter "configurations:Debug"` applies the lines below it only to Debug,
  until the next `filter`; `filter {}` goes back to every configuration.
- A Lua `function` here is just a list of settings, called inside each project
  that wants them.

```lua
workspace "PillowFort"
    architecture "x86_64"
    location "Build/Projects"
    startproject "SandboxGame"
    configurations { "Debug", "Release", "Dist" }

outputdir = "%{cfg.buildcfg}-%{cfg.system}-%{cfg.architecture}"

local vulkanSDK = os.getenv("VULKAN_SDK")
if not vulkanSDK then
    error("VULKAN_SDK is not set. Install the Vulkan SDK and open a new shell.")
end

-- Settings shared by every target we write ourselves.
local function apply_common_cpp_settings()
    language "C++"
    cppdialect "C++20"
    staticruntime "Off"
    warnings "Extra"

    targetdir ("Build/Artifacts/%{cfg.buildcfg}/%{prj.name}")
    objdir ("Build/Intermediate/" .. outputdir .. "/%{prj.name}")

    includedirs
    {
        "Source",
        vulkanSDK .. "/Include"          -- vulkan/, vma/, glm/ all live here
    }

    libdirs { vulkanSDK .. "/Lib" }
    links   { "vulkan-1" }

    -- GLM's switches go here once, never as a #define above an include:
    -- GLM's templates change shape with them, and two files that disagree
    -- produce two definitions of one function (Chapter 06 section 2).
    -- GLM_ENABLE_EXPERIMENTAL unlocks glm/gtx, which the older Camera uses
    -- (Chapter 10 section 3).
    defines { "GLM_ENABLE_EXPERIMENTAL", "GLM_FORCE_DEPTH_ZERO_TO_ONE" }

    filter "system:windows"
        systemversion "latest"
        defines { "NOMINMAX", "WIN32_LEAN_AND_MEAN" }

    filter "configurations:Debug"
        defines { "PF_DEBUG", "PF_VULKAN_VALIDATION" }
        symbols "On"

    filter "configurations:Release"
        defines "PF_RELEASE"
        optimize "Speed"

    filter "configurations:Dist"
        defines "PF_DIST"
        optimize "Speed"
        symbols "Off"

    filter {}
end

-- Vendor code is not ours to warn about.
local function apply_vendor_settings()
    warnings "Off"
    targetdir ("Build/Artifacts/%{cfg.buildcfg}/%{prj.name}")
    objdir ("Build/Intermediate/" .. outputdir .. "/%{prj.name}")

    filter "system:windows"
        systemversion "latest"
    filter "configurations:Debug"
        symbols "On"
    filter "configurations:Release or Dist"
        optimize "Speed"
    filter {}
end

project "GLFW"
    kind "StaticLib"
    language "C"
    cdialect "C11"
    apply_vendor_settings()

    files
    {
        "Vendor/GLFW/include/GLFW/glfw3.h",
        "Vendor/GLFW/include/GLFW/glfw3native.h",
        "Vendor/GLFW/src/internal.h",
        "Vendor/GLFW/src/platform.h",
        "Vendor/GLFW/src/mappings.h",
        "Vendor/GLFW/src/context.c",
        "Vendor/GLFW/src/init.c",
        "Vendor/GLFW/src/input.c",
        "Vendor/GLFW/src/monitor.c",
        "Vendor/GLFW/src/platform.c",
        "Vendor/GLFW/src/vulkan.c",
        "Vendor/GLFW/src/window.c",
        "Vendor/GLFW/src/egl_context.c",
        "Vendor/GLFW/src/osmesa_context.c",
        "Vendor/GLFW/src/null_init.c",
        "Vendor/GLFW/src/null_monitor.c",
        "Vendor/GLFW/src/null_window.c",
        "Vendor/GLFW/src/null_joystick.c"
    }

    filter "system:windows"
        files
        {
            "Vendor/GLFW/src/win32_init.c",
            "Vendor/GLFW/src/win32_module.c",
            "Vendor/GLFW/src/win32_joystick.c",
            "Vendor/GLFW/src/win32_monitor.c",
            "Vendor/GLFW/src/win32_time.c",
            "Vendor/GLFW/src/win32_thread.c",
            "Vendor/GLFW/src/win32_window.c",
            "Vendor/GLFW/src/wgl_context.c"
        }
        defines { "_GLFW_WIN32", "_CRT_SECURE_NO_WARNINGS" }
    filter {}

project "ImGui"
    kind "StaticLib"
    language "C++"
    cppdialect "C++20"
    apply_vendor_settings()

    files
    {
        "Vendor/ImGui/imgui.cpp",
        "Vendor/ImGui/imgui_draw.cpp",
        "Vendor/ImGui/imgui_tables.cpp",
        "Vendor/ImGui/imgui_widgets.cpp",
        "Vendor/ImGui/imgui_demo.cpp",
        "Vendor/ImGui/backends/imgui_impl_glfw.cpp",
        "Vendor/ImGui/backends/imgui_impl_vulkan.cpp"
    }

    includedirs
    {
        "Vendor/ImGui",
        "Vendor/ImGui/backends",
        "Vendor/GLFW/include",
        vulkanSDK .. "/Include"
    }

project "PillowFortEngine"
    kind "StaticLib"
    apply_common_cpp_settings()

    files
    {
        "Source/PillowFort/**.h",
        "Source/PillowFort/**.hpp",
        "Source/PillowFort/**.c",
        "Source/PillowFort/**.cpp"
    }

    includedirs
    {
        "Vendor/GLFW/include",
        "Vendor/ImGui",
        "Vendor/ImGui/backends"
    }

project "SandboxGame"
    kind "ConsoleApp"
    apply_common_cpp_settings()

    files
    {
        "Source/SandboxGame/**.h",
        "Source/SandboxGame/**.hpp",
        "Source/SandboxGame/**.c",
        "Source/SandboxGame/**.cpp"
    }

    -- main() includes engine headers that include GLFW, and from Chapter 07 on
    -- calls ImGui and its GLFW backend directly. Linking the libraries is not
    -- enough; the compiler needs their headers too.
    includedirs
    {
        "Vendor/GLFW/include",
        "Vendor/ImGui",
        "Vendor/ImGui/backends"
    }

    links { "PillowFortEngine", "GLFW", "ImGui" }
```

Keep `kind "ConsoleApp"`. A console window next to your render window is where
validation output goes, and you want to see it. Switch to `WindowedApp` for
`Dist` only, much later.

> **Rerun `GenerateProjects.bat` after adding a source file.** Premake expands
> each `**.cpp` glob when you run `GenerateProjects.bat`, not when you build,
> and writes the list of files it found into the `.vcxproj`. A file you add
> afterwards is not compiled, and the first sign is `LNK2019` for the functions
> in it. Every chapter from 02 on adds files, so regenerate after adding,
> renaming, moving, or deleting any source or shader. Two related traps: a
> project whose globs match nothing reports a successful build, produces no
> `.lib`, and fails later with `LNK1104` in whatever links it; and anything you
> change in Visual Studio's project settings is erased by the next generation.
> Build settings go in `premake5.lua`, and nowhere else.

---

## 4. Getting the submodules

They are declared in `.gitmodules` but not checked out. `git submodule status`
shows a leading `-` on both:

```bash
git submodule update --init --recursive
```

Then check that they are the versions the file lists above assume:

```bash
git submodule status
```

In this repository they are already pinned — the output shows `(3.4)` beside
GLFW and `(v1.92.9b-docking)` beside ImGui, and there is nothing more to do.
The docking branch of ImGui is the one to take: you are building a
shader-parameter workbench, and dockable, detachable panels are the difference
between a usable tool and one window of sliders. It is the same API plus
`ImGuiConfigFlags_DockingEnable`.

**Updating a pin later.** Check out the version you want inside the
submodule — `git -C Vendor/ImGui checkout <tag>`, where
`git -C Vendor/ImGui tag --list "*-docking" --sort=-v:refname | Select-Object -First 5`
lists the newest docking releases — then record it with
`git add Vendor/ImGui`. Without that, the parent repository still points at
the old commit (`git submodule status` shows a leading `+`), and a fresh clone
gets the version you replaced. The `files` list above matches GLFW 3.4;
`platform.c`, `win32_module.c`, and the `null_*.c` files are 3.4 additions, and
`Vendor/GLFW/src/CMakeLists.txt` is the authoritative list for any other
version.

Record both licenses in `THIRD_PARTY_NOTICES.md`. GLFW is
zlib/libpng, ImGui is MIT, and the SDK components you will use (VMA, GLM) are
MIT — all compatible with the MIT license already in `MIT-License.txt`.

Then generate:

```bash
./GenerateProjects.bat
```

---

## 5. Turning on validation properly

The validation layer is the most valuable tool in Vulkan development, and it
has considerably more to give than its default configuration.

There are three ways to enable it, and they compose:

**a. In code, which is what this project does.** Request
`VK_LAYER_KHRONOS_validation` in `VkInstanceCreateInfo::ppEnabledLayerNames`
under `PF_VULKAN_VALIDATION`. Covered in
[Chapter 02](02-Instance-And-Device.md). This is the version that ships, and
that anyone else building the repo gets for free.

**b. Environment variable, no code change.** Useful for bisecting whether the
layer itself is causing something:

```bash
$env:VK_INSTANCE_LAYERS="VK_LAYER_KHRONOS_validation"
```

**c. `vkconfig.exe`, for occasional extras.** The SDK GUI writes a
system-level layer override. It is the easy way to switch on, for a session,
checks the code does not ask for:

| Setting | When you want it |
| --- | --- |
| **GPU-Assisted Validation** | Instruments shaders to catch out-of-bounds descriptor and buffer access at runtime. Slow. Turn on when a shader misbehaves. |
| **Best Practices** | Vendor-agnostic and vendor-specific performance advice. Noisy; skim it once per milestone rather than leaving it on. |
| **Debug Printf** | `debugPrintfEXT()` from inside a shader. Invaluable when the alternative is inferring state from colors. Conflicts with GPU-Assisted on some driver versions; enable one at a time. |

**Leave synchronization validation out of any override.** Chapter 02 turns it
on in code, and an override's value for a setting outranks the application's,
so an override that mentions it can only get in the way. And clear the override
when you are done: it applies to every Vulkan application on the machine,
including games, and it is easy to forget you left it on.

**Check for one before you start, because it outranks your code.** An override
left behind by an earlier project — or by anything else that ran `vkconfig` —
can switch settings off that your application asks for, and does it silently.
Look for `%LOCALAPPDATA%\LunarG\vkconfig\override\vk_layer_settings.txt`: if
it exists, an override is active, and a line like
`khronos_validation.validate_sync = false` in it disables the synchronization
validation Chapter 02 turns on. Two symptoms give it away even without looking:
every validation message printed **twice** (once by the layer itself, once
through your callback), and sync validation that never fires — which Chapter
05's positive control catches. To clear it, open `vkconfig` and select no
configuration, or set the configuration you want explicitly.

---

## 6. Which shader compiler invocation to use

`glslc` is the right default: gcc-style flags, a sane CLI, and it is the
compiler the SDK ships and maintains.

One detail that will cost you an hour if you miss it: **ROADMAP names
shaders `Triangle.vert.glsl`, and `glslc` infers stage from the final
extension.** It sees `.glsl`, which maps to no stage, and fails. Pass the stage
explicitly:

```bash
glslc -fshader-stage=vertex --target-env=vulkan1.3 -g -O0 Shaders/Triangle/Triangle.vert.glsl -o Triangle.vert.spv
```

| Flag | Purpose |
| --- | --- |
| `-fshader-stage=` | `vertex`, `fragment`, `compute`, `geometry`, `tesscontrol`, `tesseval`. Required by ROADMAP's naming scheme. |
| `--target-env=vulkan1.3` | Selects the SPIR-V version and validates against 1.3 rules. |
| `-g -O0` | Debug config: keep names and line info so RenderDoc shows readable source. |
| `-O` | Release config: run the `spirv-opt` performance passes. |
| `-I Shaders/Include` | Include search path. |

Chapter 06 wires this into `premake5.lua` as a prebuild command.

---

## Exit check

- [ ] `vkcube` runs.
- [ ] `GenerateProjects.bat` completes without a Lua error.
- [ ] Debug and Release both build all four projects.
- [ ] `SandboxGame.exe` runs and prints through `ErrorReporting`'s `Log`:
      three static functions, `Log::info`, `Log::warning`, and `Log::error`,
      each taking a `const char*`, which every later chapter calls.
- [ ] Deleting `Build/` and regenerating reproduces both configurations.
- [ ] Add an empty `Scratch.cpp` under `Source/PillowFort/` and build: it is
      in neither Solution Explorer nor the build output. Run
      `GenerateProjects.bat`, build again, and it is in both. Delete it and
      regenerate once more.

Next: [02 — Instance, Device, and Queues](02-Instance-And-Device.md)

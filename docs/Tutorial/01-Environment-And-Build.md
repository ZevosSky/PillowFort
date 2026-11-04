# 01 — Environment and Build Wiring

**Goal:** a workspace that compiles, links the Vulkan loader, builds GLFW and
ImGui from the pinned submodules, and switches validation on in Debug for the
instance Chapter 02 creates.

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
  [index](../VulkanTutorial.md). The cost is that their versions follow the
  SDK you installed, not a pin in this repository: a newer SDK can bring a
  VMA or GLM with a changed API. Pin them as submodules instead if two
  machines must build identical code.
- **Slang is available**, and this tutorial does not use it: every shader here
  is GLSL. Both compile to SPIR-V; switching later would replace the shader
  compiler commands and their tracked inputs, not the Vulkan pipeline API.

Verify the toolchain from a fresh PowerShell session (the SDK installer sets
`VULKAN_SDK` and `PATH` only for processes started after it ran), before
anything else depends on it:

```bash
echo $env:VULKAN_SDK; where.exe glslc; vkcube.exe
```

`vkcube` spinning is the fastest proof that the loader finds your driver and
can present to a window. (The *loader* is `vulkan-1.dll`, which every Vulkan
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
uses the name rather than the line that declared it. Used without `..`, as in
`includedirs { vulkanSdk }`, the same misspelling is silent: a `nil` in a
table constructor is simply absent, so Premake receives an empty list and
reports nothing.

**b. `libdirs` is not `links`.** `libdirs { vulkanSDK .. "/Lib" }` says where
libraries are and links none of them. Without `links { "vulkan-1" }` everything
compiles, and the link fails with a wall of
`LNK2019 unresolved external symbol vkCreateInstance`.

**c. A static library's calls resolve when the executable links.**
`PillowFortEngine` is a `StaticLib`, so the Vulkan functions it calls are looked
up only when `SandboxGame` links: the library needs the Vulkan headers, and the
executable needs the loader's import library, `vulkan-1.lib`. Putting the
headers only on the library and the import library only on the executable
works until a second executable, such as a test program, links the library and
has neither. Put both in the one function every target calls, as section 3
does.

---

## 3. The corrected workspace

**This is `premake5.lua`**, whole, as it stands at the end of this chapter;
the repository's own `premake5.lua` is a later state of the same file. It
avoids the three mistakes above and adds two libraries as vendor static
libraries: **GLFW**, which opens a window and
reports keyboard and mouse input, and **Dear ImGui**, the debug-panel library
Chapter 07 sets up.

Premake in five points, enough to read the file:

- A **workspace** is the Visual Studio solution. It holds **projects**, and
  each project becomes one `.vcxproj`.
- `kind` says what a project builds: `StaticLib` is a `.lib`, `ConsoleApp` an
  `.exe` with a console window.
- `files` lists sources, and `**` matches any number of folders deep. The
  match happens when you generate, not when you build (the box after the
  listing).
- `filter "configurations:Debug"` applies the lines below it only to Debug,
  until the next `filter`; `filter {}` goes back to every configuration.
- A Lua `function` here is a list of settings that apply to whichever project
  calls it: each call such as `includedirs` adds to the project, and the
  filter, that is current when it runs. That is why each function ends with
  `filter {}`: a filter left open inside it would still apply to the lines
  after the call.

<a id="ch01-workspace"></a>

**Attempt CH01-workspace: make the build describe the project.** The
repository already holds a finished `premake5.lua`: move it aside, write the
workspace before opening the listing below, then compare. It must generate an
x64 solution under `Build/Projects`, with Debug, Release and Dist
configurations, an engine static library and a console executable that links
it. Both use C++20; GLFW and ImGui are vendor static libraries; a missing
`VULKAN_SDK` must fail during generation with a useful message. Take our own
sources from their folders on disk with globs, not a hand-kept list. Define
`PF_VULKAN_VALIDATION` in Debug only, and `GLM_FORCE_DEPTH_ZERO_TO_ONE` and
`NOMINMAX` for every target we write; the paragraph after the listing says
which later chapter needs each. Section 4 supplies the submodules, then the
exit check tests your workspace with a clean generation and build. Do not
repair generated projects in Visual Studio: repair the definition and
regenerate.

**Acceptance:** Clean generation produces the stated x64 configurations and targets; a clean Debug build links, and a missing VULKAN_SDK reports a generation error.

**Transfer:** Rename only the console target in the workspace. Predict which project and binary names change, then regenerate and build without editing generated files.

<details>
<summary>Hint 1: separate the targets from their shared settings</summary>

The workspace groups projects; each project owns its sources and links. Put
the settings shared by your C++ targets in a Lua function, and apply it to
both. Vendor libraries need their own source lists and include directories.

</details>

<details>
<summary>Hint 2: trace the executable's dependencies</summary>

`SandboxGame` needs `PillowFortEngine`, GLFW and ImGui. A static library is
only an archive of the engine's object files, and their calls into the
loader stay unresolved inside it, so the executable must link `vulkan-1` as
well. Reset each configuration filter after applying its settings.

</details>

<details>
<summary>Hint 3: use Premake's declarations to express the contract</summary>

Use `architecture`, `location`, `configurations`, `kind`, `cppdialect`,
`files`, `includedirs`, `libdirs`, `links`, `defines` and `filter`. Read the
SDK path with `os.getenv` and call `error` if it is absent. Give each project
its own `targetdir` and `objdir`, with `%{prj.name}` in the path: when two
projects share an intermediate directory, MSBuild warns (MSB8028) that a clean
or rebuild of one can delete the other's files.

</details>

<details>
<summary>Worked solution: the corrected workspace</summary>

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
    -- (Chapter 10 section 2).
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

-- Editor export is separate from the build definition and follows the target OS.
dofile("Scripts/VSCode.lua")
```

The repository's [premake5.lua](../../premake5.lua) is this file as later
chapters grow it, beginning with Chapter 06's shader rules.

</details>

A few defines in the listing matter later more than they seem to now.
`PF_VULKAN_VALIDATION`, defined in Debug only, is what Chapter 04's renderer
reads before asking Chapter 02's instance for the validation layer.
`GLM_FORCE_DEPTH_ZERO_TO_ONE` makes GLM's projection matrices produce Vulkan's
`[0, 1]` depth instead of OpenGL's `[-1, 1]` (Chapter 10 section 2).
`NOMINMAX` stops `<windows.h>`, which the engine includes for
`IsDebuggerPresent` and `GetModuleFileNameW`, from defining `min` and `max`
macros that break `std::min` and GLM; `WIN32_LEAN_AND_MEAN` leaves the rarely
used parts of that header out. The last line loads `Scripts/VSCode.lua`, which
the repository already has: it adds a `vscode` action and writes VS Code's
IntelliSense files, and changes nothing in the Visual Studio projects
([Building with Premake](../Premake.md) covers it).

Keep `kind "ConsoleApp"`. A console window next to your render window is where
validation output goes, and you want to see it. If you ever want a `Dist`
build without it, switch that configuration to `WindowedApp` and add
`entrypoint "mainCRTStartup"`, so `main()` stays the entry point instead of the
`WinMain` a Windows-subsystem program otherwise needs; this tutorial never
does.

> **Rerun `GenerateProjects.bat` after adding a source file.** Premake expands
> each `**.cpp` glob when you run `GenerateProjects.bat`, not when you build,
> and writes the list of files it found into the `.vcxproj`. A file you add
> afterwards is not compiled, and the first sign is `LNK2019` for its functions
> once something calls them. Every chapter from 02 on adds files, so
> regenerate after adding, renaming, moving, or deleting any source or shader.
> Two related traps: a project whose globs match nothing reports a successful
> build, produces no `.lib`, and fails later with `LNK1104` in whatever links it; and anything you
> change in Visual Studio's project settings is erased by the next generation.
> Build settings go in `premake5.lua`, and nowhere else.

---

## 4. Getting the submodules

They are declared in `.gitmodules` but not checked out: `git submodule status`
shows a leading `-` on both. Check them out:

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
shader-parameter workbench, and docking lets its panels snap into one layout
instead of overlapping as loose windows. It is the same API plus docking: the
`ImGuiConfigFlags_DockingEnable` flag Chapter 07 sets, and the
`ImGui::DockBuilder*` calls in `imgui_internal.h` that the later demo panels
use to restore a layout.

**Updating a pin later.** Run `git -C Vendor/ImGui fetch --tags` and then
`git -C Vendor/ImGui checkout <tag>` (`-C` runs git inside the submodule), then
record the new commit in the parent repository with `git add Vendor/ImGui` and
a commit. Without that, `git submodule status` shows a leading `+`, the parent repository still points at
the old commit, and a fresh clone gets the version you replaced. The `files` list
above matches GLFW 3.4 (`platform.c`, `win32_module.c`, and the `null_*.c` files
are its additions); `Vendor/GLFW/src/CMakeLists.txt` is the authoritative list
for any other version.

`THIRD_PARTY_NOTICES.md` records each submodule's license and pinned
revision; update its row whenever a pin moves. GLFW is
zlib/libpng, ImGui is MIT, and the SDK components you will use (VMA, GLM) are
MIT — all compatible with the MIT license already in `MIT-License.txt`.

Then generate:

```bash
./GenerateProjects.bat
```

It writes `Build/Projects/PillowFort.sln`; open it in Visual Studio and build
with `SandboxGame` as the startup project. Each project's output lands in
`Build/Artifacts/<Config>/<Project>/`.
[Building with Premake](../Premake.md) says what else that writes, how to
build from a shell, and what Premake's other generators (make files, Xcode)
give you.

---

## 5. Turning on validation properly

The validation layer is the most valuable tool in Vulkan development, and it
has considerably more to give than its default configuration.

There are three ways to enable it, and they compose:

**a. In code, which is what this project does.** Request
`VK_LAYER_KHRONOS_validation` in `VkInstanceCreateInfo::ppEnabledLayerNames`
when `PF_VULKAN_VALIDATION` is defined, which section 3's file does for Debug
only. [Chapter 02](02-Instance-And-Device.md) requests the layer, and Chapter
04's `VulkanRenderer::initialize` turns the define into that request. Because it is in the code,
anyone who builds Debug gets validation with no setup.

**b. Environment variable, no code change.** Useful on a Release build, which
does not request the layer: the same binary then runs with and without it,
which tells you whether the layer itself changes what you see. The variable
lasts for that shell only:

```bash
$env:VK_INSTANCE_LAYERS="VK_LAYER_KHRONOS_validation"
```

**c. Vulkan Configurator, for occasional extras.** The SDK's GUI,
`vkconfig-gui.exe` (in SDK 1.4.357 `vkconfig.exe` is its command-line
version), writes a layer override that applies to every Vulkan program your
Windows account runs. It is the easy way to switch on checks the code does not
ask for, and they stay on until you clear the override:

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
`khronos_validation.validate_sync = false` overrides an application's request
through that same setting. Chapter 02 deliberately uses the separate legacy
`enables` setting, so that particular `false` entry alone does not establish
that this program's synchronization validation is off. Repeated messages
(once by the layer itself, once through your callback) can reveal extra layer
configuration; Chapter 05's deliberately broken-barrier control establishes
whether synchronization validation actually fires. To clear the override,
open `vkconfig-gui` and select no
configuration, or run `vkconfig layers --surrender`, which hands layer control
back to applications; or set the configuration you want explicitly.

---

## 6. Which shader compiler invocation to use

`glslc` is the right default for its gcc-style flags (`-o`, `-I`, `-D`, `-O`).
It is built on glslang, the same front end as `glslangValidator`, the
reference compiler the SDK ships beside it.

One detail that will cost you an hour if you miss it: **ROADMAP names
shaders `Triangle.vert.glsl`, and `glslc` infers stage from the final
extension.** It sees `.glsl`, which maps to no stage, and fails. Pass the stage
explicitly:

```bash
glslc -fshader-stage=vertex --target-env=vulkan1.3 -g -O0 Shaders/Triangle/Triangle.vert.glsl -o Triangle.vert.spv
```

`--target-env=vulkan1.3` makes glslc check against Vulkan 1.3's rules and
emit SPIR-V 1.6, the highest version a 1.3 driver must accept. A shader that
includes the shared headers also needs `-I Shaders/Include`, the include search
path. The alternatives to `-fshader-stage` are naming the file
`Triangle.vert`, which glslc maps to a stage itself, or a
`#pragma shader_stage(vertex)` line in the shader; this project keeps
ROADMAP's names and passes the stage from them. Chapter 06 section 1
wires the command into `premake5.lua` as a tracked custom-build rule and says
what `-g -O0` and `-O` are for. An edit to a shader, or to an include it uses,
then rebuilds like an edited `.cpp`; adding or removing a shader file still
needs `GenerateProjects.bat`, for the same reason as a new `.cpp` (the box in
section 3).

---

## Exit check

- [ ] `vkcube` runs.
- [ ] `GenerateProjects.bat` completes without a Lua error.
- [ ] Debug and Release both build all four projects.
- [ ] In Debug, `SandboxGame.exe` runs and prints through `ErrorReporting`'s
      `Log`: three static functions, `Log::info`, `Log::warning`, and
      `Log::error`, each taking a `const char*`, which every later chapter
      calls. The print proves the executable links the engine library. A
      Release run prints nothing, and that is correct: the placeholder
      `Main.cpp` calls `Log.h`'s `LOG_INFO` macro, which compiles to nothing
      unless MSVC's `_DEBUG` is defined.
- [ ] Deleting `Build/`, regenerating, and building again reproduces both
      configurations.
- [ ] Add an empty `Scratch.cpp` under `Source/PillowFort/` and build: it is
      in neither Solution Explorer nor the build output. Run
      `GenerateProjects.bat`, build again, and it is in both. Delete it and
      regenerate once more.

Next: [02 — Instance, Device, and Queues](02-Instance-And-Device.md)

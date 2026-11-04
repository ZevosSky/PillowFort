# Building PillowFort with Premake

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

How the build works, how to run it every day, and what the other Premake
actions give you. [Chapter 01](Tutorial/01-Environment-And-Build.md) writes the
`premake5.lua` this page uses, Chapters 06 and 13 add its shader rules and
TinyUSDZ, and [ROADMAP.md](../ROADMAP.md) makes Premake authoritative for
compiling and linking (Guardrail 3). The first two sections are all you need to
build the project. Everything after them is optional.

---

## What Premake does here

Premake compiles nothing. It reads `premake5.lua` and writes project files for
another tool to build: for this project, a Visual Studio solution and one
`.vcxproj` per project. Chapter 01's `premake5.lua` describes four projects
(GLFW and ImGui as static libraries, `PillowFortEngine` as a static library,
`SandboxGame` as the executable); Chapter 13 adds TinyUSDZ as a fifth static
library, and the `--tutorial-tests` option adds the focused checks in
`Tests/TutorialHarness/`. There are three configurations, x64 only: `Debug`
defines `PF_DEBUG` and `PF_VULKAN_VALIDATION` and builds symbols, `Release`
(`PF_RELEASE`) optimizes for speed, and `Dist` (`PF_DIST`) optimizes and builds
no symbols. Premake itself is `Vendor\premake5\premake5.exe`, version
5.0.0-beta8; `--version` prints it, and `--help` lists the actions it has.

**The one rule: Premake expands the `**.cpp` globs when it generates, not when
you build.** The `.vcxproj` holds the list of files it found at the last
generation. Adding, renaming, moving, or deleting a source or shader file means
rerunning `GenerateProjects.bat`; editing a file that exists does not. Chapter 01
section 3 has the symptoms of forgetting (`LNK2019` for the new file's
functions, or `LNK1104` when a project matched no files and built no `.lib`).

Everything under `Build/` is generated. Never edit a `.vcxproj`, and never
change a setting in the Visual Studio UI: the next generation erases both. Source
files go on disk, and build settings go in `premake5.lua`.

---

## The everyday path

You need Visual Studio 2022 and the Vulkan SDK (the index's
[What you need](VulkanTutorial.md#what-you-need-and-what-it-teaches) has the
details), and `VULKAN_SDK` must be set in the shell that runs Premake:
`premake5.lua` stops with `VULKAN_SDK is not set` otherwise. The shader step
reads it again at build time, so start Visual Studio or MSBuild from an
environment that has it too; one opened before the SDK was installed does not.
After cloning, run these from the repository root:

```powershell
git submodule update --init --recursive     # once
.\GenerateProjects.bat
```

Rerun the submodule command after a pull that moves a pin, which
`git submodule status` shows as a leading `+`. The island's heightmap and
material maps, the ground textures and the Horizon plants under `Assets/`, and
two folders under `ThirdPartyScenes/`, are Git LFS (`.gitattributes`). A clone
made without Git LFS holds small pointer files there, and Horizon draws noise
or plain ground (Chapter 36's and 38's troubleshooting tables) until
`git lfs pull` and a rebuild copy the real files beside the executable.

The script moves to its own folder, stops if `Vendor\premake5\premake5.exe` is
missing, runs `premake5.exe vs2022` with any arguments you gave the script
(`.\GenerateProjects.bat --tutorial-tests` adds the test projects), and returns
Premake's exit code. Running `Vendor\premake5\premake5.exe vs2022` yourself
from the root does the same. Premake prints one `Generated ...` line per file
and ends with `Done`.

Open `Build/Projects/PillowFort.sln` in Visual Studio, pick `Debug`, `Release`,
or `Dist` on x64, and build; `SandboxGame` is the startup project. From a
shell, the same build is:

```powershell
& "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64
```

The path is the Community edition's; in a Developer PowerShell for VS 2022,
`msbuild` alone finds the installed one. The example bounds both project
scheduling and compiler workers to one; `/nr:false` also avoids retaining an
MSBuild worker afterward. From Chapter 13 TinyUSDZ enables parallel compilation
(`/MP`), so limiting projects alone does not bound the compiler work. Bare `/m`
uses the machine's core count and can exhaust memory on that template-heavy
first build. Raise the explicit limits together only when memory permits.
Microsoft's [C++ build-throughput notes](https://devblogs.microsoft.com/cppblog/cpp-build-throughput-investigation-and-tune-up/)
explain the MultiToolTask and global process controls.
The [verification harness](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/README.md) uses the same
one-worker policy and adds this project's memory preflight.

Where things land:

```text
Build/
  Projects/                       the .sln and .vcxproj files
  Artifacts/<Config>/<Project>/   SandboxGame.exe; each project's .lib; for
                                  SandboxGame, Shaders/**/*.spv beside the .exe
  Intermediate/<Config>-windows-x86_64/<Project>/   object files
  IntelliSense/<Config>/          compile_commands.json for VS Code (below)
```

From Chapter 13 on, a post-build step also copies `Assets/` into
`Artifacts/<Config>/SandboxGame/Assets/`, and the program writes
`pipeline_cache.bin` beside the `.exe` when it shuts down (Chapter 06
section 6). Each shader stage is a tracked custom-build item (Chapter 06
section 1): editing a stage recompiles that stage, and editing any shared
include recompiles every stage.

**Regenerate** when you add, rename, move, or delete a source or shader file;
when you edit `premake5.lua` or `Scripts/VSCode.lua`; after a `git pull` that
did either; and after installing or moving the Vulkan SDK, because
`premake5.lua` writes the SDK's include and library paths into the projects at
generation time (the shader step reads `$(VULKAN_SDK)` later, when it builds).
Until you regenerate, the projects still name the old SDK's headers and
libraries, which fails if that SDK is gone and mixes versions if it is not.
A plain regeneration also drops the `--tutorial-tests` projects; pass the option
each time you want them.

**Clean** by deleting `Build/`. ROADMAP Guardrail 4 holds that deleting it and
regenerating must always work. `premake5 clean` does nothing in this version: it
prints `The clean action has not yet been ported`. `.vscode/` is outside
`Build/` (and ignored by git), so delete it too if you want it gone; left alone,
it points at compilation databases under `Build/` until you regenerate.

---

## Other routes (optional)

The project targets Windows and MSVC (ROADMAP's host is Windows x64). Premake
can write other kinds of project from the same `premake5.lua`; these are
starting points, not supported builds, and `premake5.lua` stays the only build
description. `premake5` below is `Vendor\premake5\premake5.exe` on Windows;
on Linux or macOS you need a build of the same Premake version for that system.
To get another system's files from your machine, add `--os=<system>`; on that
system itself leave it off.

Each action was run once, on main's `premake5.lua` (Chapter 01's four
projects, without TinyUSDZ or the per-file shader rules), with a Linux build of
premake 5.0.0-beta8. All of them generated without a warning or an error. None
of their output was built on Windows or macOS, and the only build tried was one
`make` on Linux; "untested here" below means not tried in that run. This
branch's `premake5.lua` has grown since, and every gap named below is still in
it. The repository's `premake5.exe` has the same exporters in its embedded
scripts.

### Make files

```bash
premake5 gmake
make -C Build/Projects config=debug      # debug, release, or dist; "make help" lists them
```

You get `Build/Projects/Makefile` and one `.make` file per project.
`gmakelegacy`, the older exporter kept in this version, writes the same names.

It does not build on Linux. The first error is in GLFW's first file:
`unknown type name 'clockid_t'`, because GLFW is built as strict `-std=c11`,
which hides the POSIX types its Linux code needs (the same file compiles with
`-std=gnu11`). More errors wait behind it: `premake5.lua` gives GLFW only its
Win32 sources (under `filter "system:windows"`), so any other system gets only
GLFW's null platform, which opens no window; the engine links `-lvulkan-1`, the
Windows loader's name (Linux's is `-lvulkan`); the shader step runs
`glslc.exe`, and in this branch's file ends each command with cmd's
`|| exit /b 1`; and the finished engine calls Win32 (`windows.h` in
`DebugBreak.h` and `ExecutableFiles.cpp`).
Making it build is work in `premake5.lua` and in the code, and it is not on the
roadmap.

### Xcode

```bash
premake5 xcode4
```

You get `Build/Projects/PillowFort.xcworkspace` and one `.xcodeproj` for each
project. It generated here; Xcode was not available, so opening and building
are untested here. The output shows the make files' gaps: GLFW has no Cocoa
sources and no `_GLFW_COCOA`, the link line has `-lvulkan-1`, and a Mac has no
native Vulkan driver (the SDK ships MoltenVK, which the loader lists only to an
instance that enables `VK_KHR_portability_enumeration`, and this code does
not). Expect it to need that work and more.

### CMake

There is no CMake action in this Premake. `premake5 --help` lists `codelite`,
`gmake`, `gmakelegacy`, `ninja`, `vs2005` to `vs2026`, `xcode4`, and a few
housekeeping actions; the `modules/` folder and the changelog have nothing that
writes a `CMakeLists.txt`. The community modules page links a separate exporter,
`Jarod42/premake-cmake`, loaded with `require`. It is not part of Premake, not
in this repository, and untested here. Its `CMakeLists.txt` would be generated
from `premake5.lua`, like the make files, so Premake would stay authoritative
(Guardrail 3) as long as nobody hand-edits the output. The cost is a module
from outside Premake to vendor and keep working with beta8, and Guardrail 5
admits a dependency only when it removes work that is not part of the goal.

### VS Code

`Scripts/VSCode.lua` adds a `vscode` action. It writes IntelliSense settings
only, not a build or a debug setup: `.vscode/c_cpp_properties.json` and, per
configuration, `Build/IntelliSense/<Config>/compile_commands.json`, which lists
every source file with its own project's flags, defines, and include
directories. The C/C++ extension (`ms-vscode.cpptools`) reads them.

On Windows you do not run it: the `vs2022` action calls it after it writes the
solution, so `GenerateProjects.bat` refreshes both. (`vs2026` does not.) To run
it alone on Linux (on Windows, `premake5 vscode` with no `--cc` uses MSVC, its
default there; `--cc=gcc` would describe a compiler the projects do not use):

```bash
premake5 --cc=gcc vscode      # or --cc=clang, on Linux
```

On Linux this wrote the settings with the right compiler and `linux-gcc-x64`
mode. On Windows it finds Visual Studio 2022's MSVC compiler with `vswhere`,
untested in that run; `Tests/Python/test_vscode_export.py`, which the readme
describes, checks the result with compiler probes. The files are overwritten each time, so edit
`premake5.lua`, not them. The repository's [readme.md](../readme.md) has more
on the VS Code setup, including the Linux harness options.

---

## At a glance

| Action | Command | Status for this project |
| --- | --- | --- |
| `vs2022` | `.\GenerateProjects.bat` | The supported build; also writes the VS Code files |
| `gmake`, `gmakelegacy` | `premake5 gmake` | Generates; does not build on Linux because GLFW is strict C11 with Win32-only sources, the link names `vulkan-1`, and the shader step runs `glslc.exe` |
| `xcode4` | `premake5 xcode4` | Generates; untested here |
| `vscode` | `premake5 --cc=gcc vscode` | IntelliSense settings only; ran on Linux, untested here on Windows |
| `vs2026` | `premake5 vs2026` | Generates a `.slnx`; untested here |
| `codelite`, `ninja` | `premake5 codelite` | Generates; untested here (`ninja` has the make files' gaps) |
| CMake | none | Not in this premake; the community `premake-cmake` module is untested here |

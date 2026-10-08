# PillowFort

A small Vulkan engine for relearning Vulkan and building graphics demos.

- [ROADMAP.md](ROADMAP.md) — scope, decisions, current step, and the build order.
- [docs/Tutorial/](docs/Tutorial/) — 34-chapter Vulkan walkthrough used as reference.

Todo list
---------

1. [ ]  Demo of the project / brief project at a glance
2. [ ]  .... make more of this list

# Current requirements

1. premake5 (included)
2. Visual Studio 2022 with Desktop development with C++
3. Windows SDK
4. Vulkan SDK 1.3 & compatible GPU

## Libraries

1. imgui
2. GLFW

## Build

```
git submodule update --init --recursive
GenerateProjects.bat
```

Then build `Build/Projects/PillowFort.sln`. Rerun `GenerateProjects.bat` after
adding or removing any source file.

## VS Code IntelliSense

Install the Microsoft C/C++ extension (`ms-vscode.cpptools`) and open the
repository root in VS Code. The editor helper in `Scripts/VSCode.lua` exports
`.vscode/c_cpp_properties.json` and a compilation database for each configuration
under `Build/IntelliSense/`. Each source file gets its own project's compiler,
language standard, include directories, and defines. Engine-only dependencies
stay out of SandboxGame's include path. Headers without a matching source use
the engine configuration as a fallback.

On Windows, `GenerateProjects.bat` also runs this export and detects the VS 2022
x64 compiler. On Linux, use a Linux Premake 5 executable to export editor settings:

```bash
premake5 --cc=gcc vscode
# Or: premake5 --cc=clang vscode
```

The Linux verification of the reference branches uses the
[tutorial harness from main](https://github.com/ZevosSky/PillowFort/tree/main/Tests/TutorialHarness).
Those branches do not contain the harness. Pass its directory from another
checkout when generating their editor settings:

```bash
premake5 --cc=gcc --linux-harness-dir=/path/to/main/Tests/TutorialHarness vscode
```

This exports the harness's platform shim include directory and Debug `_DEBUG`
define for engine and game sources. `--linux-harness` is shorthand when the
harness lives in this checkout. GLFW is built separately by the harness's CMake
step, so its source commands are omitted in harness mode. The `vscode` action
writes editor settings only; use the existing harness commands for Linux builds.

Use **C/C++: Select a Configuration** to choose `Debug`, `Release`, or `Dist` to
match the configuration you are building. Rerun the platform's export command
after changing build settings, compiler, or the Vulkan SDK location. `VULKAN_SDK`
must point to that machine's SDK, with the `Include` layout expected by Premake
and the harness. The generated file is local and overwritten on regeneration;
keep build settings in `premake5.lua`.

If an already-open VS Code window still shows stale errors, run **C/C++: Reset
IntelliSense Database**, then **Developer: Reload Window**. The compilation
database selects the settings when you open a source file.

To check the generated settings with native compiler probes, run these in a
Visual Studio developer shell or a configured Linux shell:

```powershell
python Tests/Python/test_vscode_export.py --premake Vendor/premake5/premake5.exe
```

```bash
python3 Tests/Python/test_vscode_export.py --premake /path/to/premake5 \
    --compiler gcc --linux-harness-dir /path/to/main/Tests/TutorialHarness
```

Use `--compiler clang` to check Clang. The checks cover Debug, Release, and Dist,
compile C++20 Vulkan/GLM/GLFW/ImGui header probes, and verify private TinyUSDZ
include isolation on reference branches. Logs and probes stay under
`Build/EditorTests/`.

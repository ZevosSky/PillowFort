# Getting Started

This is the reproducible setup guide for PillowFort. The root `readme.md` is a
scratch board and is not part of the build contract.

The current project is a headless C++ learning slice: an engine static library,
a sandbox executable that advances three frames, and a small executable test.
GLFW, Vulkan, shader compilation, and ImGui are planned but are not wired into
the build yet.

## Current prerequisites

- Windows 10 or 11 on x64.
- Git with submodule support.
- Visual Studio 2022 with **Desktop development with C++**.
- The MSVC v143 toolset with C++20 support.
- A Windows 10 or 11 SDK.

Premake is checked in at `Vendor/premake5/premake5.exe`. A Vulkan SDK and
Vulkan-capable GPU are not required until the Vulkan milestone begins.

## Prepare a checkout

From the repository root in PowerShell:

```powershell
git submodule update --init --recursive
git submodule status
```

Both submodule status lines should begin with a space. A leading `-` means the
submodule still needs initialization; a leading `+` means it is checked out at
a different revision than the repository pins.

## Generate the Visual Studio solution

```powershell
.\GenerateProjects.bat
```

The command creates `Build/Projects/PillowFort.sln` with these targets:

- `PillowFortEngine`: the engine static library;
- `SandboxGame`: the current executable learning slice; and
- `PillowFortTests`: CPU-only regression tests.

`Build/` is generated and ignored. Do not edit generated solution or project
files; change `premake5.lua` and regenerate instead.

## Build

Open the solution in Visual Studio, select `Debug` or `Release` and `x64`, then
build the solution. From a **Developer PowerShell for VS 2022**, the equivalent
commands are:

```powershell
msbuild .\Build\Projects\PillowFort.sln /m /p:Configuration=Debug /p:Platform=x64
msbuild .\Build\Projects\PillowFort.sln /m /p:Configuration=Release /p:Platform=x64
```

If `msbuild` is not found, use the Developer PowerShell installed with Visual
Studio or build from the IDE.

## Run and test

After a Debug build:

```powershell
.\Build\Artifacts\Debug\SandboxGame\SandboxGame.exe
.\Build\Artifacts\Debug\PillowFortTests\PillowFortTests.exe
```

The Debug sandbox should trace startup, complete three frames, trace shutdown,
and return success. The test executable should print `PASS: EngineLoop tests`
and return success. The Release executables use the same paths under
`Build/Artifacts/Release`; successful lifecycle trace calls are compiled out
there.

## Reproduce from clean generated output

Close Visual Studio, remove the disposable `Build/` directory, and repeat the
generate, build, run, and test commands above. Source code and dependency
submodules remain untouched.

## Where to go next

- [plan.md](../plan.md) is the sole completion checklist and names the next
  exercise.
- [ROADMAP.md](../ROADMAP.md) explains scope, ownership, and deferred choices.
- [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) records redistributed
  dependencies and their licenses.

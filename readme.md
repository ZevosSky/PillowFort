# PillowFort

PillowFort is an early-stage C++20 game-engine learning project for Windows. Its
foundation uses Premake, Vulkan 1.3, GLFW, and Dear ImGui.

The current project intentionally has no Python build layer or reflection
generator. Premake is the single build definition, and runtime behavior remains
explicit C++.

## Current status

The repository and Premake workspace are scaffolded. The next implementation
step is a minimal `ErrorReporting` library call from `SandboxGame::main()`.

See [plan.md](plan.md) for chronological tasks and [ROADMAP.md](ROADMAP.md) for
scope and architectural decisions.

## Requirements

- Windows x64.
- Git with submodule support.
- Visual Studio 2022 with the **Desktop development with C++** workload.
- A Vulkan 1.3-capable GPU and current driver.
- The Vulkan SDK, including validation layers and `glslc`.

Premake is included at `Vendor/premake5/premake5.exe`. GLFW and Dear ImGui are
pinned Git submodules.

The Windows SDK supplies the Windows headers, libraries, and tools used by MSVC
to build a native Windows application. It is normally installed with the
Visual Studio C++ workload.

Python is not required.

## Set up an existing clone

From the repository root:

```powershell
git submodule update --init --recursive
.\GenerateProjects.bat
```

This generates:

```text
Build/Projects/PillowFort.sln
```

Open that solution in Visual Studio and select either Debug or Release.

From a Visual Studio Developer PowerShell, the generated solution can
eventually be built directly:

```powershell
msbuild Build/Projects/PillowFort.sln /m /p:Configuration=Debug /p:Platform=x64
```

The executable output belongs under:

```text
Build/Artifacts/<Configuration>/SandboxGame/
```

`Build/` is generated and may be deleted at any time.

## Repository layout

```text
Source/PillowFort/   Engine C++ modules
Source/SandboxGame/  Test application and main()
Shaders/             Handwritten GLSL
Tests/Cpp/           Focused C++ tests
Vendor/              Premake and pinned dependencies
Build/               Disposable generated projects and build output
```

## Project rules

- Build settings live in `premake5.lua`.
- Engine objects are explicitly constructed and owned.
- Vulkan code stays explicit until another graphics backend is genuinely
  needed.
- Automation is introduced only after a repeated manual pattern is understood.
- Possible future Python code generation must remain offline and must not
  become a game runtime dependency.

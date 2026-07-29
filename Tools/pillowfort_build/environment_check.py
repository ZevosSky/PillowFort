"""Inspect whether this machine can develop and build PillowFort.

TODO:
- Check Python 3.11+, Windows x64, Premake, MSVC/MSBuild, the Windows SDK, the
  Vulkan SDK, and ``glslc``.
- Confirm the GLFW and ImGui submodules exist at their expected paths.
- Report detected versions and exact fixes for missing or incompatible tools.
- Return structured results so tests do not need to scrape printed messages.
- Keep checks read-only: never install tools, download dependencies, or update
  submodules from this module.

All filesystem paths should be ``pathlib.Path`` values. External processes must
receive argument lists so spaces in repository and SDK paths work correctly.
"""

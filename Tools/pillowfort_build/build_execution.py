"""Prepare build inputs and invoke the generated MSBuild solution.

TODO:
- Accept only supported configurations and platforms.
- Ensure generated Premake inputs and projects are current.
- Prepare generated files and compile invalid shaders before C++ compilation.
- Locate and invoke MSBuild without constructing a shell command string.
- Stream useful compiler output and preserve the build tool's failure status.
- Keep output under ``Build/Projects`` and ``Build/Artifacts``.

The Visual Studio pre-build path must call preparation only. It must never call
this module in a way that starts another Visual Studio/MSBuild build.
"""

"""Generate deterministic Premake inputs and invoke Premake.

TODO:
- Convert validated project data into
  ``Build/Generated/PremakeInputs.generated.lua``.
- Emit ``Build/Generated/ResolvedProject.json`` for human diagnostics only.
- Sort all generated collections and omit timestamps and machine-specific
  absolute paths.
- Use ``generated_file_cache`` for atomic write-if-changed behavior.
- Invoke the vendored Premake executable with an argument list and an explicit
  repository working directory.
- Keep target definitions, compiler/linker flags, source globs, include paths,
  libraries, and configurations authoritative in ``premake5.lua``.

Project generation may validate configuration and run Premake. It must not
compile shaders or invoke MSBuild.
"""

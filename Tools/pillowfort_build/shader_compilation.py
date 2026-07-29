"""Discover GLSL sources and incrementally compile them to SPIR-V.

TODO:
- Recognize only documented shader-stage suffixes such as ``.vert.glsl`` and
  ``.frag.glsl``.
- Invoke ``glslc`` for Vulkan 1.3 with Debug/Release-specific options.
- Request compiler dependency files and include transitive include contents in
  each cache key.
- Hash compiler identity, options, stage, source, and dependencies so only
  invalid outputs rebuild.
- Write SPIR-V and a deterministic ``CompiledShaderCatalog.json`` beside the
  selected executable.
- Use ``generated_file_cache`` for locking, atomic replacement, and ownership.

This command compiles shaders only. It must never invoke Premake or MSBuild.
"""

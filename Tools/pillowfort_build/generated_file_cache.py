"""Safely own, update, and clean files produced by PillowFort tooling.

TODO:
- Write UTF-8/LF content atomically and only when bytes have changed.
- Store deterministic generation/cache records beneath
  ``Build/Intermediate/PillowFortBuild``.
- Prevent concurrent writers from corrupting an output or ownership record.
- Record every owned generated path before offering cleanup.
- Refuse cleanup for paths outside ``Build`` or absent from the ownership
  record.
- Provide small reusable operations rather than knowledge of Premake, shaders,
  modules, or C++ schemas.

Generated output is disposable, but arbitrary user files are not. Every delete
operation must prove that the target is both owned and inside the Build tree.
"""

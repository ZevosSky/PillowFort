"""Validate and order module/application dependencies.

TODO:
- Check that every dependency names a declared module.
- Reject self-dependencies and cycles with the complete readable cycle path.
- Produce a stable topological order, using name sorting whenever more than one
  valid order exists.
- Resolve each application's transitive module set for Premake generation.
- Provide a deterministic graph view for ``pillowfort.py module graph``.

This module works only with names and dependency relationships. It must not
read TOML, inspect source files, or invoke build tools.
"""

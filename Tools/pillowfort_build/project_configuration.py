"""Load and validate the single handwritten ``PillowFort.toml`` file.

TODO:
- Locate the repository root without depending on the caller's working
  directory.
- Parse TOML with the Python 3.11 standard-library ``tomllib`` module.
- Represent project, graphics, module, and application data with small typed
  immutable values.
- Reject unknown keys, wrong value types, invalid names, and missing source
  roots with messages that include the TOML key involved.
- Ask ``module_dependencies`` to validate references and dependency cycles.
- Derive paths, namespaces, target membership, and dependency order rather than
  storing those values in additional configuration files.

The TOML file remains the source of truth. Generated JSON or Lua must never be
read back as authoritative configuration.
"""

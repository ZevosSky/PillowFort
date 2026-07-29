"""Preview and create a module from the proven PillowFort module shape.

TODO:
- Validate the requested name with the same rules used by configuration
  loading.
- Calculate all proposed directories, starter files, and TOML edits first.
- Print a preview and make mutation an explicit second step.
- Refuse to overwrite any existing path.
- Update only one complete assignment in ``[modules]`` or ``[applications]``;
  never parse and rewrite the entire TOML document.
- Use temporary files and atomic replacement when applying the TOML edit.

Do not implement this generator until at least two real modules establish the
handwritten C++ pattern it is meant to reproduce.
"""

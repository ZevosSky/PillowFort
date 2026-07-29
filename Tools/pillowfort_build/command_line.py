"""Parse PillowFort commands and route them to one owning module.

Planned public entry:
    main(argv: Sequence[str] | None = None) -> int

TODO:
- Build the documented command tree with ``argparse``.
- Keep parsing separate from execution so command behavior can be unit tested.
- Load the project configuration once and pass it to the selected operation.
- Print diagnostics from ``error_messages`` and return stable exit codes.
- Add ``--help`` examples for environment, project, build, shader, module,
  configuration, and test commands.

This module coordinates commands; it must not contain Premake, MSBuild, shader,
or file-generation implementation details.
"""





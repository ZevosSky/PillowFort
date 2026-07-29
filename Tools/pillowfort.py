"""Command-line entry point for PillowFort development tools.

This file must stay thin. It will import ``main`` from
``pillowfort_build.command_line`` and exit with the integer status it returns.
All validation, generation, compilation, and build behavior belongs in the
package modules, not here.
"""

# TODO:
# 1. Import command_line.main after that function is implemented.
# 2. Call it under an ``if __name__ == "__main__"`` guard.
# 3. Convert only expected PillowFort errors into clean process exit codes;
#    unexpected exceptions should keep their traceback while the tooling is
#    under development.


if __name__ == "__main__":
    from pillowfort_build.command_line import main

    raise NotImplementedError("Command-line entry point is not yet implemented.")
    
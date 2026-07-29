"""Define consistent, actionable failures for PillowFort development tools.

TODO:
- Define a small base exception for expected user-correctable failures.
- Carry a short problem statement, relevant path or configuration key, and a
  concrete suggested fix as structured data.
- Format diagnostics in one place for the command-line layer.
- Preserve external process exit codes and concise command context.
- Keep internal programming errors distinct so they retain normal tracebacks.

This module defines and formats errors; it must not print, exit the process, or
perform environment checks itself.
"""


class PillowFortError(Exception): 
    # An expected failure that the user can correct by changing the environment, project configuration, or command-line arguments.

    '''
    Python's version of a class constructor is the __init__ method. It is called when an instance of the class is created. 
    The self parameter refers to the instance being created, and the other parameters are used to initialize the instance's attributes.
    '''
    def __init__(self, problem: str, *, suggestion: str | None = None) -> None:
        super().__init__(problem)
        self.problem = problem 
        self.suggestion = suggestion

        
def format_error(error: PillowFortError) -> str:
    """Format a PillowFortError for printing to the console/command-line."""

    if error.problem is None:
        raise ValueError("PillowFortError must have a problem description.")

    lines = [f"Error: {error.problem}"] # f before the string allows for variable interpolation

    if error.suggestion is not None:
        lines.append(f"Fix: {error.suggestion}")

    return "\n".join(lines)

    
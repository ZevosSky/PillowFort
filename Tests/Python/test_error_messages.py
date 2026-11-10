'''
    @author Gary Yang 
    @date 7/29/2026
    @copyright 2026 Gary Yang

    Basic unit test for the python builder error handling 
'''

import unittest

from Tools.pillowfort_build.error_messages import (
    PillowFortError,
    format_error,
)


class ErrorMessageTests(unittest.TestCase):
    def test_formats_problem_without_suggestion(self) -> None:
        error = PillowFortError("Premake was not found.")

        result = format_error(error)

        self.assertEqual(result, "Error: Premake was not found.")

    def test_formats_problem_and_suggestion(self) -> None:
        error = PillowFortError(
            "Premake was not found.",
            suggestion="Place Premake in Vendor/premake5.",
        )

        result = format_error(error)

        self.assertEqual(
            result,
            "Error: Premake was not found.\n"
            "Fix: Place Premake in Vendor/premake5.",
        )

    def test_exception_string_contains_the_problem(self) -> None:
        error = PillowFortError("The configuration is invalid.")

        self.assertEqual(str(error), "The configuration is invalid.")


if __name__ == "__main__":
    unittest.main()


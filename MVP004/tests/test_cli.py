from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from hydranet.cli import main


class CliTests(unittest.TestCase):
    def test_main_without_arguments_runs_demo(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = main([])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Success: True", output)
        self.assertIn("Connection flows:", output)

    def test_cli_can_print_continuation_trace_as_csv(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = main(
                [
                    "demo",
                    "--solver",
                    "continuation_solver",
                    "--continuation-steps",
                    "3",
                    "--trace-csv",
                ]
            )

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("problem_scale", output)
        self.assertIn("solver_name", output)


if __name__ == "__main__":
    unittest.main()

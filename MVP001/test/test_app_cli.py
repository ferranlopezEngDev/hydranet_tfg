"""Automated checks for the first command-line application entry point."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app_cli import main
from src.application import load_network


class AppCliTests(unittest.TestCase):
    """Exercise the CLI flows expected by the first application version."""

    def test_cli_script_runs_directly_and_shows_help_without_args(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "src/app_cli.py")],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("hydranet-cli", result.stdout)
        self.assertIn("interactive numbered menu", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_menu_command_supports_numbered_navigation(self) -> None:
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()

        with (
            patch("builtins.input", side_effect=["9", "0"]),
            redirect_stdout(stdout_buffer),
            redirect_stderr(stderr_buffer),
        ):
            exit_code = main(["menu"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("Hydranet Menu", stdout_buffer.getvalue())
        self.assertIn("Available solvers", stdout_buffer.getvalue())
        self.assertIn("Bye.", stdout_buffer.getvalue())

    def test_no_args_uses_numbered_menu_in_tty_mode(self) -> None:
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", side_effect=["0"]),
            redirect_stdout(stdout_buffer),
            redirect_stderr(stderr_buffer),
        ):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("Hydranet Menu", stdout_buffer.getvalue())
        self.assertIn("0. Exit", stdout_buffer.getvalue())

    def test_non_menu_subcommands_are_rejected(self) -> None:
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = main(["summary", "network.json"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertIn("only supports interactive menu navigation", stderr_buffer.getvalue())

    def test_menu_can_create_and_delete_network_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            network_path = Path(temporary_directory) / "network.json"
            stdout_buffer = StringIO()
            stderr_buffer = StringIO()

            with (
                patch(
                    "builtins.input",
                    side_effect=["2", str(network_path), "10", "", "y", "0"],
                ),
                redirect_stdout(stdout_buffer),
                redirect_stderr(stderr_buffer),
            ):
                exit_code = main(["menu"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr_buffer.getvalue(), "")
            self.assertIn("Created empty network", stdout_buffer.getvalue())
            self.assertIn("Deleted network file", stdout_buffer.getvalue())
            self.assertFalse(network_path.exists())

    def test_menu_can_open_sample_network_and_show_summary(self) -> None:
        network_path = (
            Path(__file__).resolve().parents[1]
            / "networks"
            / "cli_cases"
            / "01_single_pipe_valid.json"
        )
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()

        with (
            patch("builtins.input", side_effect=["1", str(network_path), "3", "", "0"]),
            redirect_stdout(stdout_buffer),
            redirect_stderr(stderr_buffer),
        ):
            exit_code = main(["menu"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("Opened network", stdout_buffer.getvalue())
        self.assertIn("Network summary", stdout_buffer.getvalue())
        self.assertIn("Connections: 1", stdout_buffer.getvalue())
        self.assertEqual(load_network(str(network_path)).getConnectionCount(), 1)

    def test_menu_can_browse_for_existing_network_file(self) -> None:
        sample_source_path = (
            Path(__file__).resolve().parents[1]
            / "networks"
            / "cli_cases"
            / "06_single_dw_pipe_valid.json"
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            case_directory = Path(temporary_directory) / "cases"
            case_directory.mkdir()
            browsed_network_path = case_directory / "network.json"
            browsed_network_path.write_text(
                sample_source_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            stdout_buffer = StringIO()
            stderr_buffer = StringIO()
            original_cwd = Path.cwd()

            try:
                os.chdir(temporary_directory)

                with (
                    patch(
                        "builtins.input",
                        side_effect=["1", "b", "1", "1", "3", "", "0"],
                    ),
                    redirect_stdout(stdout_buffer),
                    redirect_stderr(stderr_buffer),
                ):
                    exit_code = main(["menu"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr_buffer.getvalue(), "")
            self.assertIn("Path Browser", stdout_buffer.getvalue())
            self.assertIn("Opened network", stdout_buffer.getvalue())
            self.assertIn("Network summary", stdout_buffer.getvalue())
            self.assertIn("Connections: 1", stdout_buffer.getvalue())

    def test_menu_can_browse_for_output_path_when_creating_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "output"
            output_directory.mkdir()
            output_path = output_directory / "created.json"
            stdout_buffer = StringIO()
            stderr_buffer = StringIO()
            original_cwd = Path.cwd()

            try:
                os.chdir(temporary_directory)

                with (
                    patch(
                        "builtins.input",
                        side_effect=["2", "b", "1", "n", "created.json", "0"],
                    ),
                    redirect_stdout(stdout_buffer),
                    redirect_stderr(stderr_buffer),
                ):
                    exit_code = main(["menu"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr_buffer.getvalue(), "")
            self.assertIn("Path Browser", stdout_buffer.getvalue())
            self.assertIn("Created empty network", stdout_buffer.getvalue())
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()

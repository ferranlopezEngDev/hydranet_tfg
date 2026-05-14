from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from hydranet.launcher import main


class LauncherTests(unittest.TestCase):
    def test_launcher_routes_to_gui_when_no_arguments_are_provided(self) -> None:
        with patch("hydranet.launcher.gui_main", return_value=0) as mocked_gui:
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        mocked_gui.assert_called_once_with(())

    def test_launcher_routes_to_gui_subcommand(self) -> None:
        with patch("hydranet.launcher.gui_main", return_value=0) as mocked_gui:
            exit_code = main(["gui", "examples/single_pipe.json"])

        self.assertEqual(exit_code, 0)
        mocked_gui.assert_called_once_with(("examples/single_pipe.json",))

    def test_launcher_routes_cli_commands_to_cli_main(self) -> None:
        with patch("hydranet.launcher.cli_main", return_value=0) as mocked_cli:
            exit_code = main(["solve", "examples/single_pipe.json"])

        self.assertEqual(exit_code, 0)
        mocked_cli.assert_called_once_with(("solve", "examples/single_pipe.json"))

    def test_launcher_help_explains_gui_and_cli(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = main(["--help"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Hydranet MVP004", output)
        self.assertIn("hydranet gui", output)
        self.assertIn("open the desktop GUI", output)


if __name__ == "__main__":
    unittest.main()

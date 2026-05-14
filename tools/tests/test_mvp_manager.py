from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools import mvp_manager


class MVPManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifests = mvp_manager.discover_manifests()

    def test_discover_manifests_finds_expected_versions(self) -> None:
        self.assertIn("MVP001", self.manifests)
        self.assertIn("MVP002", self.manifests)
        self.assertIn("MVP003", self.manifests)

    def test_latest_alias_resolves_to_highest_version(self) -> None:
        manifest = mvp_manager.resolve_manifest(self.manifests, "latest")
        self.assertEqual(manifest.name, "MVP003")

    def test_numeric_alias_resolves_to_zero_padded_name(self) -> None:
        manifest = mvp_manager.resolve_manifest(self.manifests, "mvp2")
        self.assertEqual(manifest.name, "MVP002")

    def test_build_command_uses_manifest_templates(self) -> None:
        manifest = self.manifests["MVP001"]
        command = mvp_manager.build_command(manifest, "run", platform_key="posix")

        self.assertTrue(command[0].endswith("/MVP001/.venv/bin/python"))
        self.assertEqual(command[1], "src/app_cli.py")

    def test_list_command_prints_versions(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = mvp_manager.main(["list"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("MVP001", output)
        self.assertIn("MVP002", output)
        self.assertIn("MVP003", output)

    def test_find_clean_targets_skips_venv_and_detects_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".venv" / "lib" / "__pycache__").mkdir(parents=True)
            (root / ".venv" / "lib" / "__pycache__" / "ignored.pyc").write_bytes(b"x")
            (root / "module" / "__pycache__").mkdir(parents=True)
            (root / "module" / "__pycache__" / "kept.pyc").write_bytes(b"x")
            (root / "module" / "artifact.pyc").write_bytes(b"x")
            (root / ".coverage").write_text("", encoding="utf-8")

            targets = mvp_manager.find_clean_targets(root)

            self.assertIn(root / "module" / "__pycache__", targets)
            self.assertIn(root / "module" / "artifact.pyc", targets)
            self.assertIn(root / ".coverage", targets)
            self.assertNotIn(root / ".venv" / "lib" / "__pycache__", targets)

    def test_clean_command_dry_run_reports_targets(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = mvp_manager.main(["clean", "MVP001", "--dry-run"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("[clean] MVP001", output)


if __name__ == "__main__":
    unittest.main()

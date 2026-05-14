#!/usr/bin/env python3
"""Lightweight manager for versioned Hydranet MVPs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILENAME = "mvp.json"
ACTION_ORDER = ("install", "install_checks", "run", "test")
CLEAN_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov"}
CLEAN_FILE_SUFFIXES = {".pyc", ".pyo"}
CLEAN_FILE_NAMES = {".coverage", "coverage.xml"}


class UserError(Exception):
    """Raised when user input or local workspace state is invalid."""


@dataclass(frozen=True)
class MVPManifest:
    """Metadata and delegated commands for a single MVP."""

    name: str
    display_name: str
    description: str
    kind: str
    python_min: str
    directory: Path
    documents: tuple[str, ...]
    commands: dict[str, dict[str, list[str]]]


def current_platform() -> str:
    return "windows" if os.name == "nt" else "posix"


def version_number(name: str) -> int:
    match = re.search(r"(\d+)$", name)
    return int(match.group(1)) if match else -1


def manifest_sort_key(manifest: MVPManifest) -> tuple[int, str]:
    return (version_number(manifest.name), manifest.name)


def resolve_venv_python(mvp_dir: Path, platform_key: str | None = None) -> Path:
    platform_name = platform_key or current_platform()
    if platform_name == "windows":
        return mvp_dir / ".venv" / "Scripts" / "python.exe"
    return mvp_dir / ".venv" / "bin" / "python"


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise UserError(f"Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise UserError(f"Invalid JSON manifest at {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise UserError(f"Manifest must be a JSON object: {path}")
    return data


def require_str(data: Mapping[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise UserError(f"Manifest field '{key}' must be a non-empty string: {path}")
    return value


def parse_documents(data: Mapping[str, Any], path: Path) -> tuple[str, ...]:
    raw_documents = data.get("documents", [])
    if not isinstance(raw_documents, list) or not all(
        isinstance(item, str) and item for item in raw_documents
    ):
        raise UserError(f"Manifest field 'documents' must be a list of strings: {path}")
    return tuple(raw_documents)


def parse_commands(data: Mapping[str, Any], path: Path) -> dict[str, dict[str, list[str]]]:
    raw_commands = data.get("commands")
    if not isinstance(raw_commands, dict):
        raise UserError(f"Manifest field 'commands' must be an object: {path}")

    commands: dict[str, dict[str, list[str]]] = {}
    for action, raw_platform_map in raw_commands.items():
        if not isinstance(action, str) or not isinstance(raw_platform_map, dict):
            raise UserError(f"Invalid command definition for '{action}' in {path}")

        platform_map: dict[str, list[str]] = {}
        for platform_key, raw_tokens in raw_platform_map.items():
            if platform_key not in {"posix", "windows"}:
                raise UserError(
                    f"Unsupported platform '{platform_key}' in action '{action}' ({path})"
                )
            if not isinstance(raw_tokens, list) or not all(
                isinstance(token, str) and token for token in raw_tokens
            ):
                raise UserError(
                    f"Command tokens for '{action}/{platform_key}' must be a string list: {path}"
                )
            platform_map[platform_key] = raw_tokens

        commands[action] = platform_map

    missing_actions = [action for action in ("install", "run", "test") if action not in commands]
    if missing_actions:
        joined = ", ".join(missing_actions)
        raise UserError(f"Manifest missing required action(s) {joined}: {path}")

    return commands


def load_manifest(path: Path) -> MVPManifest:
    data = load_json(path)
    name = require_str(data, "name", path)
    if name != path.parent.name:
        raise UserError(
            f"Manifest name '{name}' must match its folder '{path.parent.name}': {path}"
        )

    return MVPManifest(
        name=name,
        display_name=require_str(data, "display_name", path),
        description=require_str(data, "description", path),
        kind=require_str(data, "kind", path),
        python_min=require_str(data, "python_min", path),
        directory=path.parent,
        documents=parse_documents(data, path),
        commands=parse_commands(data, path),
    )


def discover_manifests(repo_root: Path = REPO_ROOT) -> dict[str, MVPManifest]:
    manifests: dict[str, MVPManifest] = {}
    for child in sorted(repo_root.iterdir()):
        manifest_path = child / MANIFEST_FILENAME
        if child.is_dir() and manifest_path.is_file():
            manifest = load_manifest(manifest_path)
            manifests[manifest.name.upper()] = manifest
    return manifests


def sorted_manifests(manifests: Mapping[str, MVPManifest]) -> list[MVPManifest]:
    return sorted(manifests.values(), key=manifest_sort_key)


def latest_manifest(manifests: Mapping[str, MVPManifest]) -> MVPManifest:
    ordered = sorted_manifests(manifests)
    if not ordered:
        raise UserError("No MVP manifests found in the repository root.")
    return ordered[-1]


def resolve_manifest(manifests: Mapping[str, MVPManifest], identifier: str) -> MVPManifest:
    if not manifests:
        raise UserError("No MVP manifests found in the repository root.")

    cleaned = identifier.strip()
    if not cleaned:
        raise UserError("You must provide an MVP identifier.")

    if cleaned.lower() in {"latest", "current"}:
        return latest_manifest(manifests)

    direct = manifests.get(cleaned.upper())
    if direct is not None:
        return direct

    digits_match = re.fullmatch(r"(?:mvp)?0*(\d+)", cleaned, flags=re.IGNORECASE)
    if digits_match:
        requested_version = int(digits_match.group(1))
        matches = [
            manifest
            for manifest in manifests.values()
            if version_number(manifest.name) == requested_version
        ]
        if len(matches) == 1:
            return matches[0]

    available = ", ".join(manifest.name for manifest in sorted_manifests(manifests))
    raise UserError(f"Unknown MVP '{identifier}'. Available values: {available}, latest")


def render_context(manifest: MVPManifest, platform_key: str | None = None) -> dict[str, str]:
    platform_name = platform_key or current_platform()
    venv_python = resolve_venv_python(manifest.directory, platform_name)
    return {
        "repo_root": str(REPO_ROOT),
        "mvp_dir": str(manifest.directory),
        "venv_dir": str(manifest.directory / ".venv"),
        "venv_python": str(venv_python),
    }


def build_command(
    manifest: MVPManifest,
    action: str,
    platform_key: str | None = None,
) -> list[str]:
    platform_name = platform_key or current_platform()
    platform_commands = manifest.commands.get(action)
    if platform_commands is None:
        raise UserError(f"{manifest.name} does not define the action '{action}'.")

    tokens = platform_commands.get(platform_name)
    if tokens is None:
        raise UserError(
            f"{manifest.name} does not define the action '{action}' for platform '{platform_name}'."
        )

    context = render_context(manifest, platform_name)
    return [token.format_map(context) for token in tokens]


def display_command(command: Sequence[str]) -> str:
    return shlex.join(command)


def is_installed(manifest: MVPManifest, platform_key: str | None = None) -> bool:
    return resolve_venv_python(manifest.directory, platform_key).exists()


def action_label(action: str) -> str:
    return action.replace("_", "-")


def available_actions(manifest: MVPManifest, platform_key: str | None = None) -> list[str]:
    platform_name = platform_key or current_platform()
    actions: list[str] = []
    for action in ACTION_ORDER:
        if platform_name in manifest.commands.get(action, {}):
            actions.append(action)
    for action in manifest.commands:
        if action not in ACTION_ORDER and platform_name in manifest.commands[action]:
            actions.append(action)
    return actions


def print_list(manifests: Mapping[str, MVPManifest]) -> None:
    ordered = sorted_manifests(manifests)
    newest = latest_manifest(manifests).name if ordered else None

    print("Available MVPs:")
    for manifest in ordered:
        status = "installed" if is_installed(manifest) else "not installed"
        latest_suffix = " (latest)" if manifest.name == newest else ""
        print(f"- {manifest.name}{latest_suffix} [{status}] {manifest.description}")


def print_info(manifest: MVPManifest) -> None:
    print(f"{manifest.display_name} ({manifest.name})")
    print(f"Path: {manifest.directory}")
    print(f"Kind: {manifest.kind}")
    print(f"Python: {manifest.python_min}")
    print(f"Installed: {'yes' if is_installed(manifest) else 'no'}")
    print(f"Description: {manifest.description}")
    print("Actions:")
    for action in available_actions(manifest):
        command = build_command(manifest, action)
        print(f"  {action_label(action)}: {display_command(command)}")
    if manifest.documents:
        print("Documents:")
        for document in manifest.documents:
            print(f"  {manifest.directory.name}/{document}")


def find_clean_targets(root: Path) -> list[Path]:
    targets: list[Path] = []

    for current_dir, dirnames, filenames in os.walk(root):
        current_path = Path(current_dir)

        kept_dirnames: list[str] = []
        for dirname in dirnames:
            if dirname in {".git", ".venv"}:
                continue
            candidate = current_path / dirname
            if dirname in CLEAN_DIR_NAMES:
                targets.append(candidate)
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in filenames:
            candidate = current_path / filename
            if candidate.suffix in CLEAN_FILE_SUFFIXES or filename in CLEAN_FILE_NAMES:
                targets.append(candidate)

    return sorted(targets)


def remove_paths(paths: Sequence[Path], dry_run: bool = False) -> int:
    if not paths:
        print("No generated cache files found.")
        return 0

    action = "Would remove" if dry_run else "Removing"
    for path in paths:
        print(f"{action}: {path}")
        if dry_run:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    print(f"Removed {len(paths)} path(s)." if not dry_run else f"Would remove {len(paths)} path(s).")
    return 0


def clean_workspace(
    manifests: Mapping[str, MVPManifest],
    identifier: str | None = None,
    dry_run: bool = False,
) -> int:
    if identifier:
        if identifier.lower() == "workspace":
            root = REPO_ROOT
            label = "workspace"
        else:
            manifest = resolve_manifest(manifests, identifier)
            root = manifest.directory
            label = manifest.name
    else:
        root = REPO_ROOT
        label = "workspace"

    print(f"[clean] {label}")
    print(f"root: {root}")
    paths = find_clean_targets(root)
    return remove_paths(paths, dry_run=dry_run)


def run_action(manifest: MVPManifest, action: str, dry_run: bool = False) -> int:
    command = build_command(manifest, action)
    print(f"[{manifest.name}] {action_label(action)}")
    print(f"cwd: {manifest.directory}")
    print(f"command: {display_command(command)}")

    if dry_run:
        return 0

    if action in {"run", "test"} and not is_installed(manifest):
        raise UserError(
            f"{manifest.name} is not installed yet. Run 'python3 mvp.py install {manifest.name}' first."
        )

    try:
        completed = subprocess.run(command, cwd=manifest.directory, check=False)
    except FileNotFoundError as exc:
        raise UserError(f"Command not found while running {manifest.name}/{action}: {exc}") from exc

    return completed.returncode


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install, run, and inspect Hydranet MVP versions from the repo root."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List all discovered MVP versions.")

    info_parser = subparsers.add_parser("info", help="Show metadata and commands for one MVP.")
    info_parser.add_argument("mvp", help="MVP identifier, for example MVP003 or latest.")

    install_parser = subparsers.add_parser("install", help="Run the install command for one MVP.")
    install_parser.add_argument("mvp", help="MVP identifier, for example MVP002 or latest.")
    install_parser.add_argument(
        "--checks",
        action="store_true",
        help="Use the optional install+verification command when the MVP defines one.",
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command without executing it.",
    )

    run_parser = subparsers.add_parser("run", help="Launch one installed MVP.")
    run_parser.add_argument("mvp", help="MVP identifier, for example MVP001 or latest.")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command without executing it.",
    )

    test_parser = subparsers.add_parser("test", help="Run the automated tests for one MVP.")
    test_parser.add_argument("mvp", help="MVP identifier, for example MVP003 or latest.")
    test_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command without executing it.",
    )

    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove generated cache and test-artifact files from the workspace or one MVP.",
    )
    clean_parser.add_argument(
        "mvp",
        nargs="?",
        help="Optional MVP identifier. Omit it to clean the whole workspace.",
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the paths that would be removed without deleting them.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        manifests = discover_manifests()

        if args.command == "list":
            print_list(manifests)
            return 0

        if args.command == "clean":
            return clean_workspace(manifests, args.mvp, dry_run=args.dry_run)

        manifest = resolve_manifest(manifests, args.mvp)

        if args.command == "info":
            print_info(manifest)
            return 0

        if args.command == "install":
            action = "install_checks" if args.checks else "install"
            return run_action(manifest, action, dry_run=args.dry_run)

        if args.command == "run":
            return run_action(manifest, "run", dry_run=args.dry_run)

        if args.command == "test":
            return run_action(manifest, "test", dry_run=args.dry_run)

        raise UserError(f"Unsupported command '{args.command}'.")
    except UserError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${1:-$ROOT_DIR/.venv}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: Python interpreter '$PYTHON_BIN' not found." >&2
  echo "Set PYTHON_BIN=/path/to/python3 or install Python 3 first." >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"

cat <<EOF
MVP001 installation complete.

Virtual environment:
  $VENV_DIR

Activate it:
  source "$VENV_DIR/bin/activate"

Run the CLI menu:
  "$VENV_DIR/bin/python" "$ROOT_DIR/src/app_cli.py"

Run the full test suite:
  cd "$ROOT_DIR"
  "$VENV_DIR/bin/python" -m unittest discover -s test -p 'test_*.py'
EOF

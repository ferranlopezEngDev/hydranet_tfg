#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${1:-$ROOT_DIR/.venv}"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Error: virtual environment Python not found at '$VENV_PYTHON'." >&2
  echo "Run 'bash \"$ROOT_DIR/install.sh\"' first." >&2
  exit 1
fi

exec "$VENV_PYTHON" "$ROOT_DIR/src/main.py"

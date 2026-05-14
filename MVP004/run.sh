#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Virtual environment not found. Bootstrapping MVP004 first..." >&2
  bash "$ROOT_DIR/install.sh"
fi

if [[ "$#" -eq 0 ]]; then
  exec "$VENV_PYTHON" "$ROOT_DIR/src/main.py"
fi

exec "$VENV_PYTHON" "$ROOT_DIR/src/main.py" "$@"

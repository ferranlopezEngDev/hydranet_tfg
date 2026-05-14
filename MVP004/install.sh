#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${1:-$ROOT_DIR/.venv}"
RUN_CHECKS="${RUN_CHECKS:-0}"
REQUIRED_PYTHON_VERSION="${REQUIRED_PYTHON_VERSION:-3.11}"
LOCAL_TOOLS_DIR="$ROOT_DIR/.tools/bin"
LOCAL_UV_BIN="$LOCAL_TOOLS_DIR/uv"

python_meets_requirement() {
  local python_bin="$1"
  local required_version="$2"

  "$python_bin" - <<PY >/dev/null
import sys

required = tuple(int(part) for part in "${required_version}".split("."))
if sys.version_info < required:
    raise SystemExit(1)
PY
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi

  if [[ -x "$LOCAL_UV_BIN" ]]; then
    printf '%s\n' "$LOCAL_UV_BIN"
    return 0
  fi

  mkdir -p "$LOCAL_TOOLS_DIR"
  echo "Compatible Python not found. Bootstrapping local uv..." >&2

  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh \
      | env UV_INSTALL_DIR="$LOCAL_TOOLS_DIR" UV_NO_MODIFY_PATH=1 sh >&2
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh \
      | env UV_INSTALL_DIR="$LOCAL_TOOLS_DIR" UV_NO_MODIFY_PATH=1 sh >&2
  else
    echo "Error: curl or wget is required to bootstrap uv and install Python." >&2
    exit 1
  fi

  if [[ ! -x "$LOCAL_UV_BIN" ]]; then
    echo "Error: uv bootstrap completed but '$LOCAL_UV_BIN' was not created." >&2
    exit 1
  fi

  printf '%s\n' "$LOCAL_UV_BIN"
}

install_managed_python() {
  local uv_bin="$1"

  echo "Installing Python $REQUIRED_PYTHON_VERSION with uv..." >&2
  "$uv_bin" python install "$REQUIRED_PYTHON_VERSION" >&2

  local managed_python
  managed_python="$("$uv_bin" python find "$REQUIRED_PYTHON_VERSION")"
  if [[ -z "$managed_python" || ! -x "$managed_python" ]]; then
    echo "Error: uv did not return a usable Python executable." >&2
    exit 1
  fi

  printf '%s\n' "$managed_python"
}

resolve_python_bin() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    if command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
      if python_meets_requirement "${PYTHON_BIN}" "$REQUIRED_PYTHON_VERSION"; then
        printf '%s\n' "${PYTHON_BIN}"
        return 0
      fi

      echo "Requested interpreter '${PYTHON_BIN}' is older than Python $REQUIRED_PYTHON_VERSION." >&2
      local uv_bin
      uv_bin="$(ensure_uv)"
      install_managed_python "$uv_bin"
      return 0
    fi

    echo "Error: Python interpreter '${PYTHON_BIN}' not found." >&2
    local uv_bin
    uv_bin="$(ensure_uv)"
    install_managed_python "$uv_bin"
    return 0
  fi

  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if python_meets_requirement "$candidate" "$REQUIRED_PYTHON_VERSION"; then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done

  local uv_bin
  uv_bin="$(ensure_uv)"
  install_managed_python "$uv_bin"
}

PYTHON_BIN="$(resolve_python_bin)"

"$PYTHON_BIN" - <<PY
import sys

required = tuple(int(part) for part in "${REQUIRED_PYTHON_VERSION}".split("."))
if sys.version_info < required:
    raise SystemExit(
        f"Python {'.'.join(str(part) for part in required)} or newer is required for MVP004. "
        f"Detected: {sys.version.split()[0]}"
    )

print(f"Using Python {sys.version.split()[0]}")
PY

"$PYTHON_BIN" -m venv "$VENV_DIR"
VENV_PYTHON="$VENV_DIR/bin/python"

"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
"$VENV_PYTHON" -m pip install -e "$ROOT_DIR"
"$VENV_PYTHON" -m pip check

"$VENV_PYTHON" - <<'PY'
import importlib

for module_name in ("hydranet", "numpy", "scipy", "tkinter"):
    importlib.import_module(module_name)

print("Dependency smoke check OK.")
PY

if [[ "$RUN_CHECKS" == "1" ]]; then
  echo "Running optional verification checks..."
  "$VENV_PYTHON" -m compileall "$ROOT_DIR/src" "$ROOT_DIR/tests"
  "$VENV_PYTHON" -m unittest discover -s "$ROOT_DIR/tests" -p "test_*.py"
fi

cat <<EOF
MVP004 installation complete.

Virtual environment:
  $VENV_DIR

Activate it:
  source "$VENV_DIR/bin/activate"

Open the desktop app:
  "$VENV_PYTHON" "$ROOT_DIR/src/main.py"
  or after activating the environment:
  python "$ROOT_DIR/src/main.py"
  or
  bash "$ROOT_DIR/run.sh"
  or
  hydranet

Run the technical CLI demo:
  "$VENV_PYTHON" "$ROOT_DIR/src/main.py" demo
  or after activating the environment:
  hydranet demo

Optional full verification:
  RUN_CHECKS=1 bash "$ROOT_DIR/install.sh"
EOF

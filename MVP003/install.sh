#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${1:-$ROOT_DIR/.venv}"
RUN_CHECKS="${RUN_CHECKS:-0}"

resolve_python_bin() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    if command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
      printf '%s\n' "${PYTHON_BIN}"
      return 0
    fi

    echo "Error: Python interpreter '${PYTHON_BIN}' not found." >&2
    exit 1
  fi

  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  echo "Error: no suitable Python interpreter found." >&2
  echo "Install Python 3.11+ or set PYTHON_BIN=/path/to/python." >&2
  exit 1
}

PYTHON_BIN="$(resolve_python_bin)"

"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit(
        "Python 3.11 or newer is required for MVP003. "
        f"Detected: {sys.version.split()[0]}"
    )

print(f"Using Python {sys.version.split()[0]}")
PY

"$PYTHON_BIN" -m venv "$VENV_DIR"
VENV_PYTHON="$VENV_DIR/bin/python"

"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
"$VENV_PYTHON" -m pip install -r "$ROOT_DIR/requirements.txt"
"$VENV_PYTHON" -m pip check

"$VENV_PYTHON" - <<'PY'
import importlib
import platform

required_modules = ("numpy", "scipy", "matplotlib", "tkinter")
missing_modules: list[tuple[str, Exception]] = []

for module_name in required_modules:
    try:
        importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - installer smoke check
        missing_modules.append((module_name, exc))

if missing_modules:
    print("Dependency smoke check failed:")
    for module_name, exc in missing_modules:
        print(f"  - {module_name}: {exc}")

    if any(module_name == "tkinter" for module_name, _ in missing_modules):
        system_name = platform.system()
        print("")
        print("`tkinter` is required to launch the GUI.")
        if system_name == "Linux":
            print("Install it from your distribution package manager.")
            print("Example on Debian/Ubuntu: sudo apt install python3-tk")
        elif system_name == "Darwin":
            print("Use a Python build that ships with Tk support.")
        else:
            print("Reinstall Python with Tcl/Tk support enabled.")

    raise SystemExit(1)

print("Dependency smoke check OK.")
PY

if [[ "$RUN_CHECKS" == "1" ]]; then
  echo "Running optional verification checks..."
  "$VENV_PYTHON" -m compileall "$ROOT_DIR/src" "$ROOT_DIR/test"
  "$VENV_PYTHON" -m unittest discover -s "$ROOT_DIR/test" -p "test_*.py"
fi

cat <<EOF
MVP003 installation complete.

Virtual environment:
  $VENV_DIR

Activate it:
  source "$VENV_DIR/bin/activate"

Run the GUI:
  "$VENV_PYTHON" "$ROOT_DIR/src/main.py"
  or
  bash "$ROOT_DIR/run.sh"

Optional full verification:
  RUN_CHECKS=1 bash "$ROOT_DIR/install.sh"
EOF

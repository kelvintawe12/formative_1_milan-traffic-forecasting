#!/usr/bin/env bash
# Create .venv and install all dependencies. Idempotent.
#
# Usage:
#   ./scripts/00_setup_env.sh           # CPU torch (default)
#   ./scripts/00_setup_env.sh --cuda    # CUDA 12.1 torch
#   PYTHON=python3.11 ./scripts/00_setup_env.sh   # pick interpreter

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON="${PYTHON:-python3}"
CUDA=0

for arg in "$@"; do
  case "$arg" in
    --cuda) CUDA=1 ;;
    *) echo "Unknown arg: $arg" >&2; exit 64 ;;
  esac
done

section() { printf '\n=== %s ===\n' "$*"; }

section "Checking Python"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python not found at '$PYTHON'. Install Python 3.10 or 3.11 and re-run." >&2
  exit 1
fi
"$PYTHON" --version

section "Creating virtual environment"
if [[ -d "$VENV_DIR" ]]; then
  echo ".venv already exists at $VENV_DIR (re-using)"
else
  "$PYTHON" -m venv "$VENV_DIR"
  echo "Created $VENV_DIR"
fi

# pick the right venv python (Windows-style Scripts or *nix bin)
if [[ -x "$VENV_DIR/bin/python" ]]; then
  VENV_PY="$VENV_DIR/bin/python"
elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
  VENV_PY="$VENV_DIR/Scripts/python.exe"
else
  echo "venv python not found under $VENV_DIR" >&2
  exit 1
fi

section "Upgrading pip / wheel"
"$VENV_PY" -m pip install --upgrade pip wheel setuptools

section "Installing project dependencies"
"$VENV_PY" -m pip install -r "$PROJECT_ROOT/requirements.txt"

if [[ "$CUDA" == "1" ]]; then
  section "Installing CUDA build of torch"
  "$VENV_PY" -m pip install --upgrade \
    --index-url https://download.pytorch.org/whl/cu121 torch
fi

section "Smoke import test"
"$VENV_PY" - <<'PY'
import sys
mods = ['numpy', 'pandas', 'pyarrow', 'matplotlib', 'seaborn',
        'statsmodels', 'sklearn', 'torch', 'tqdm']
bad = []
for m in mods:
    try:
        __import__(m); print(f'  OK   {m}')
    except Exception as e:
        bad.append((m, str(e))); print(f'  FAIL {m}: {e}')
if bad: sys.exit(1)
PY

section "Done"
echo "Activate with:  source .venv/bin/activate  (Linux/macOS)"
echo "             or .\\.venv\\Scripts\\Activate.ps1  (Windows)"
echo "Next:           ./scripts/01_download_data.sh"

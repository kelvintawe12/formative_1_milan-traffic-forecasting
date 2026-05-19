#!/usr/bin/env bash
# Download the Milan telecom dataset from Harvard Dataverse via the public API.
# Idempotent — re-run to retry any failed files.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/data/raw}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  VENV_PY="$PROJECT_ROOT/.venv/bin/python"
elif [[ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
  VENV_PY="$PROJECT_ROOT/.venv/Scripts/python.exe"
else
  echo "Virtual environment not found. Run scripts/00_setup_env.sh first." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

printf '\n=== Downloading Milan telecom dataset ===\n'
echo "Output directory : $OUT_DIR"
echo "Max parallel     : $MAX_PARALLEL"
echo

"$VENV_PY" "$PROJECT_ROOT/scripts/_download_dataverse.py" \
  --out-dir "$OUT_DIR" \
  --max-parallel "$MAX_PARALLEL"

printf '\n=== Verifying file count ===\n'
count=$(find "$OUT_DIR" -maxdepth 1 -name '*.txt' | wc -l | tr -d ' ')
echo "Found $count .txt file(s) in $OUT_DIR"
if [[ "$count" -lt 60 ]]; then
  echo "WARNING: expected ~62 daily files. Got $count. Re-run this script to retry." >&2
fi

printf '\n=== Done ===\n'
echo "Next: ./scripts/02_smoke_test.sh"

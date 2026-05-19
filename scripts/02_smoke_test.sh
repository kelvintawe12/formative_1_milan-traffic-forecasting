#!/usr/bin/env bash
# Smoke-test the loader on one day before kicking off the full run.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$PROJECT_ROOT/data/raw"
SMOKE_IN="$PROJECT_ROOT/data/raw_one_day"
SMOKE_OUT="$PROJECT_ROOT/data/processed/smoke"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  VENV_PY="$PROJECT_ROOT/.venv/bin/python"
elif [[ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
  VENV_PY="$PROJECT_ROOT/.venv/Scripts/python.exe"
else
  echo "Virtual environment not found. Run scripts/00_setup_env.sh first." >&2
  exit 1
fi

first_txt=$(find "$RAW_DIR" -maxdepth 1 -name '*.txt' | sort | head -n 1)
if [[ -z "$first_txt" ]]; then
  echo "No .txt files found in $RAW_DIR. Run scripts/01_download_data.sh first." >&2
  exit 1
fi

printf '\n=== Smoke test on %s ===\n' "$(basename "$first_txt")"
mkdir -p "$SMOKE_IN" "$SMOKE_OUT"
cp -f "$first_txt" "$SMOKE_IN/"

"$VENV_PY" - <<PY
import os, sys, time
sys.path.insert(0, r"$PROJECT_ROOT")
from src.data.loader import build_parquet_dataset, load_area_from_parquet, memory_usage_mb

t0 = time.perf_counter()
summary = build_parquet_dataset(r"$SMOKE_IN", r"$SMOKE_OUT", chunksize=1_000_000)
print()
print(summary.to_string(index=False))
print(f'\\nElapsed: {time.perf_counter()-t0:.1f}s')

df = load_area_from_parquet(r"$SMOKE_OUT", 4159)
print(f'\\nSpot-check (area 4159): {len(df):,} rows, {memory_usage_mb(df):.2f} MB in RAM')
print(df.head())
PY

printf '\nSmoke test passed.\n'
echo "Next: ./scripts/03_run_all.sh   (several hours)"

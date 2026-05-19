#!/usr/bin/env bash
# One-button driver: setup -> download -> smoke -> run all notebooks.
#
# Usage:
#   ./scripts/run_everything.sh                     # full flow
#   ./scripts/run_everything.sh --skip-download     # data/raw already populated
#   ./scripts/run_everything.sh --skip-smoke
#   ./scripts/run_everything.sh --cuda              # install CUDA torch
#
# Each step is idempotent — re-running is safe.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_DOWNLOAD=0
SKIP_SMOKE=0
CUDA_FLAG=()

for arg in "$@"; do
  case "$arg" in
    --skip-download) SKIP_DOWNLOAD=1 ;;
    --skip-smoke)    SKIP_SMOKE=1 ;;
    --cuda)          CUDA_FLAG=(--cuda) ;;
    *) echo "Unknown arg: $arg" >&2; exit 64 ;;
  esac
done

step() {
  local name="$1"; shift
  printf '\n########################################\n'
  printf '##  %s\n' "$name"
  printf '########################################\n'
  local t0; t0=$(date +%s)
  "$@"
  local dt=$(( $(date +%s) - t0 ))
  printf '\n(%s took %02d:%02d:%02d)\n' "$name" $((dt/3600)) $(( (dt%3600)/60 )) $((dt%60))
}

step "00 setup env"      bash "$SCRIPT_DIR/00_setup_env.sh" "${CUDA_FLAG[@]}"

if [[ "$SKIP_DOWNLOAD" == "1" ]]; then
  echo "Skipping 01 download (--skip-download)."
else
  step "01 download data" bash "$SCRIPT_DIR/01_download_data.sh"
fi

if [[ "$SKIP_SMOKE" == "1" ]]; then
  echo "Skipping 02 smoke (--skip-smoke)."
else
  step "02 smoke test"    bash "$SCRIPT_DIR/02_smoke_test.sh"
fi

step "03 run all notebooks" bash "$SCRIPT_DIR/03_run_all.sh"

printf '\nALL DONE.\n'

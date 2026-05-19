#!/usr/bin/env bash
# Execute notebooks 01 -> 02 -> 03 -> 04 end-to-end.
#
# Usage:
#   ./scripts/03_run_all.sh
#   ./scripts/03_run_all.sh --skip 01 02      # skip stages already done
#   ./scripts/03_run_all.sh --only 03 04      # only run these stages
#   TIMEOUT=14400 ./scripts/03_run_all.sh     # per-cell timeout (seconds)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMEOUT="${TIMEOUT:-14400}"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  VENV_PY="$PROJECT_ROOT/.venv/bin/python"
elif [[ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
  VENV_PY="$PROJECT_ROOT/.venv/Scripts/python.exe"
else
  echo "Virtual environment not found. Run scripts/00_setup_env.sh first." >&2
  exit 1
fi

printf '\n=== Running pipeline ===\n'
echo "python run_pipeline.py --timeout $TIMEOUT $*"
cat <<EOF

This is the long one. Plan on:
  01 (data handling)  ~30-60 min
  02 (EDA)            ~5-10 min
  03 (models)         several hours  <- bottleneck (SARIMA s=144)
  04 (reporting)      ~1 min

EOF

"$VENV_PY" "$PROJECT_ROOT/run_pipeline.py" --timeout "$TIMEOUT" "$@"

printf '\nPipeline complete.\n'
echo "Outputs:"
echo "  notebooks/*.executed.ipynb     (executed notebook copies)"
echo "  outputs/figures/*.png          (all plots)"
echo "  outputs/tables/*.csv           (performance + timing tables)"
echo "  outputs/models/all_results.pkl (pickled model results)"

"""
run_pipeline.py
---------------
One-command driver that executes the four notebooks in order via
`jupyter nbconvert --execute`. Each executed notebook is written next to
the source as `<name>.executed.ipynb` so the original cells remain clean.

Usage:
    python run_pipeline.py                  # full pipeline
    python run_pipeline.py --skip 01        # skip stages already done
    python run_pipeline.py --only 03 04     # only run these stages

Stages are identified by their leading numeric prefix.
"""
from __future__ import annotations

import argparse
import os
import sys
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NOTEBOOK_DIR = ROOT / "notebooks"

STAGES = [
    ("01", "01_data_handling.ipynb"),
    ("02", "02_eda.ipynb"),
    ("03", "03_models.ipynb"),
    ("04", "04_results_reporting.ipynb"),
]


def run_stage(stage_id: str, nb_name: str, timeout: int) -> None:
    src = NOTEBOOK_DIR / nb_name
    if not src.exists():
        sys.exit(f"[{stage_id}] not found: {src}")
    out = NOTEBOOK_DIR / src.name.replace(".ipynb", ".executed.ipynb")
    print(f"\n=== Stage {stage_id}: {nb_name} ===")
    t0 = time.perf_counter()
    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "notebook",
        "--execute", str(src),
        "--output", out.name,
        "--ExecutePreprocessor.timeout", str(timeout),
    ]
    result = subprocess.run(cmd, cwd=NOTEBOOK_DIR)
    if result.returncode != 0:
        sys.exit(f"[{stage_id}] failed (exit {result.returncode})")
    print(f"[{stage_id}] OK in {time.perf_counter()-t0:.1f}s -> {out.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip", nargs="*", default=[],
        help="Stage IDs to skip (e.g. 01 02)",
    )
    parser.add_argument(
        "--only", nargs="*", default=None,
        help="Stage IDs to run, overriding the default sequence",
    )
    parser.add_argument(
        "--timeout", type=int, default=7200,
        help="Per-cell execution timeout in seconds (default 7200 = 2h)",
    )
    args = parser.parse_args()

    selected = STAGES
    if args.only:
        selected = [s for s in STAGES if s[0] in args.only]
    selected = [s for s in selected if s[0] not in args.skip]

    if not selected:
        sys.exit("Nothing to do — every stage was skipped or excluded.")

    print("Will run stages:", ", ".join(s[0] for s in selected))
    for sid, nb in selected:
        run_stage(sid, nb, args.timeout)
    print("\nPipeline finished.")


if __name__ == "__main__":
    main()

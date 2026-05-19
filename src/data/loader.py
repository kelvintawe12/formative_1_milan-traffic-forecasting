"""
src/data/loader.py
------------------
Efficient loading and memory optimization for the TIM Big Data Challenge
Milan dataset.

The raw release is ~20 GB of tab-separated text (one file per day, two months).
Each raw row is:

    square_id <TAB> time_interval <TAB> country_code <TAB>
    sms_in <TAB> sms_out <TAB> call_in <TAB> call_out <TAB> internet_traffic

For this assignment we only need (square_id, time_interval, internet_traffic),
and we must sum internet_traffic over country_code to get a single value per
(area, 10-minute interval).

Strategy (Task 1):
  1. Read each raw .txt in chunks of `chunksize` rows (pyarrow-backed pandas).
  2. Drop unused columns at read time (usecols).
  3. Downcast dtypes immediately (int32→int16 for square_id, float64→float32
     for internet_traffic).
  4. Aggregate per chunk: groupby(square_id, time_interval).sum().
  5. Stream each *aggregated* file to its own Parquet shard on disk.
  6. Never hold the full dataset in memory — downstream code reads back only
     what it needs (e.g. a single area's series) via the partitioned dataset.

The peak RAM cost is therefore O(chunksize × few-cols), not O(file size) and
not O(total dataset).
"""

from __future__ import annotations

import os
import time
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as pads
from tqdm import tqdm
from typing import Iterable


# ── Column names (note: paper [1] has the field order wrong; this is correct) ──
RAW_COLUMNS = [
    "square_id",
    "time_interval",
    "country_code",
    "sms_in",
    "sms_out",
    "call_in",
    "call_out",
    "internet_traffic",
]

# Only these are needed for the assignment.
KEEP_COLUMNS = ["square_id", "time_interval", "internet_traffic"]

# Memory-optimised target dtypes for the aggregated output.
OPTIMIZED_DTYPES = {
    "square_id":        "int16",    # 1..10000 fits in int16
    "time_interval":    "int64",    # Unix ms timestamps
    "internet_traffic": "float32",  # plenty of precision for CDR counts
}


# ── Memory helpers ────────────────────────────────────────────────────────────
def memory_usage_mb(df: pd.DataFrame) -> float:
    """Total memory usage of a DataFrame in MB (deep=True for object dtypes)."""
    return df.memory_usage(deep=True).sum() / (1024 ** 2)


# ── Per-file streaming aggregator ─────────────────────────────────────────────
def _aggregate_file_to_parquet(
    src_path: str,
    dst_path: str,
    chunksize: int = 1_000_000,
) -> dict:
    """
    Read a single raw .txt in chunks, aggregate over country_code per chunk,
    then merge the partial aggregates and write one Parquet shard.

    Returns a small report dict with raw/aggregated row counts and timing.
    """
    t0 = time.perf_counter()
    n_raw = 0
    partials: list[pd.DataFrame] = []

    reader = pd.read_csv(
        src_path,
        sep="\t",
        header=None,
        names=RAW_COLUMNS,
        usecols=KEEP_COLUMNS,
        dtype={
            "square_id":        "int32",
            "time_interval":    "int64",
            "internet_traffic": "float64",
        },
        chunksize=chunksize,
        na_values=[""],
    )

    for chunk in reader:
        n_raw += len(chunk)
        # internet_traffic is the only column that may be NaN (rows where
        # country had no Internet activity in that interval).
        chunk["internet_traffic"] = chunk["internet_traffic"].fillna(0.0)

        # Downcast before grouping — saves both compute and RAM.
        chunk["square_id"] = chunk["square_id"].astype("int16")

        agg = (
            chunk.groupby(["square_id", "time_interval"], sort=False)
                 ["internet_traffic"].sum()
                 .reset_index()
        )
        agg["internet_traffic"] = agg["internet_traffic"].astype("float32")
        partials.append(agg)

    if not partials:
        raise RuntimeError(f"No rows read from {src_path}")

    # Merge per-chunk aggregates (two (square, ts) keys may appear in
    # multiple chunks if a chunk boundary splits them).
    merged = pd.concat(partials, ignore_index=True)
    merged = (
        merged.groupby(["square_id", "time_interval"], sort=False)
              ["internet_traffic"].sum()
              .reset_index()
    )
    merged["internet_traffic"] = merged["internet_traffic"].astype("float32")
    merged["square_id"]        = merged["square_id"].astype("int16")

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    table = pa.Table.from_pandas(merged, preserve_index=False)
    pq.write_table(table, dst_path, compression="snappy")

    return {
        "src":            os.path.basename(src_path),
        "dst":            os.path.basename(dst_path),
        "raw_rows":       n_raw,
        "aggregated_rows": len(merged),
        "wall_seconds":   round(time.perf_counter() - t0, 2),
        "shard_mb":       round(os.path.getsize(dst_path) / (1024 ** 2), 2),
    }


def build_parquet_dataset(
    raw_dir: str,
    out_dir: str,
    chunksize: int = 1_000_000,
    pattern: str = ".txt",
) -> pd.DataFrame:
    """
    Convert every raw .txt in `raw_dir` into a Snappy-compressed Parquet shard
    under `out_dir`. Returns a DataFrame summarising the conversion.

    This is the entry point for Task 1: it produces a partitioned dataset that
    downstream notebooks can query selectively (one area at a time) without
    ever loading the full ~20 GB into memory.
    """
    files = sorted(f for f in os.listdir(raw_dir) if f.endswith(pattern))
    if not files:
        raise FileNotFoundError(f"No '{pattern}' files in {raw_dir}")

    print(f"Found {len(files)} raw file(s) to process → {out_dir}\n")
    os.makedirs(out_dir, exist_ok=True)
    reports = []

    for fname in tqdm(files, desc="Aggregating"):
        src = os.path.join(raw_dir, fname)
        dst = os.path.join(out_dir, fname.replace(pattern, ".parquet"))
        if os.path.exists(dst):
            # Skip already-converted shards so the job is resumable.
            reports.append({
                "src": fname, "dst": os.path.basename(dst),
                "raw_rows": None, "aggregated_rows": None,
                "wall_seconds": 0.0, "shard_mb":
                    round(os.path.getsize(dst) / (1024 ** 2), 2),
                "skipped": True,
            })
            continue
        reports.append(_aggregate_file_to_parquet(src, dst, chunksize))

    summary = pd.DataFrame(reports)
    total_mb = summary["shard_mb"].sum()
    print(f"\nWrote {len(summary)} shard(s), total {total_mb:.1f} MB on disk.")
    return summary


# ── Lazy / selective readers ──────────────────────────────────────────────────
def _open_dataset(path: str) -> pads.Dataset:
    """Open either a single .parquet file or a directory of shards."""
    return pads.dataset(path, format="parquet")


def load_from_parquet(path: str) -> pd.DataFrame:
    """
    Load the full aggregated dataset into a single DataFrame.

    Works with either:
      - a single .parquet file (legacy notebooks),
      - or a directory of shards produced by build_parquet_dataset().

    WARNING: for the full 20 GB raw → ~2 GB aggregated dataset this is still
    several GB in RAM. Prefer `load_area_from_parquet()` for Task 2 / 3 work
    on a small number of areas.
    """
    ds = _open_dataset(path)
    df = ds.to_table().to_pandas()
    # Re-apply optimized dtypes (parquet reader may upcast).
    df["square_id"] = df["square_id"].astype(OPTIMIZED_DTYPES["square_id"])
    df["internet_traffic"] = df["internet_traffic"].astype(
        OPTIMIZED_DTYPES["internet_traffic"]
    )
    return df


def load_area_from_parquet(
    path: str,
    square_ids: int | Iterable[int],
) -> pd.DataFrame:
    """
    Read only the rows for the requested square_id(s) from a Parquet dataset.

    This uses pyarrow's predicate pushdown so the data on disk is filtered
    before being materialised — typically ~3 orders of magnitude less RAM
    than `load_from_parquet` followed by a Python filter.
    """
    if isinstance(square_ids, (int, np.integer)):
        square_ids = [int(square_ids)]
    else:
        square_ids = [int(s) for s in square_ids]

    ds = _open_dataset(path)
    table = ds.to_table(filter=pads.field("square_id").isin(square_ids))
    df = table.to_pandas()
    df["square_id"] = df["square_id"].astype(OPTIMIZED_DTYPES["square_id"])
    df["internet_traffic"] = df["internet_traffic"].astype(
        OPTIMIZED_DTYPES["internet_traffic"]
    )
    return df


def total_traffic_per_area(path: str) -> pd.Series:
    """
    Sum internet_traffic per square_id across the whole dataset, using a
    streaming scan so peak RAM stays at one row-group at a time.

    Returns a Series indexed by square_id (int16) of float64 totals.
    """
    ds = _open_dataset(path)
    totals: dict[int, float] = {}
    for batch in ds.to_batches(columns=["square_id", "internet_traffic"]):
        sq = batch.column("square_id").to_numpy()
        tr = batch.column("internet_traffic").to_numpy()
        # numpy bincount is the fastest way to sum-by-key when keys are small
        # integers; square_id is in [1, 10000].
        if sq.size == 0:
            continue
        max_id = int(sq.max())
        sums = np.bincount(sq, weights=tr, minlength=max_id + 1)
        for sid in np.nonzero(sums)[0]:
            totals[int(sid)] = totals.get(int(sid), 0.0) + float(sums[sid])

    s = pd.Series(totals, name="total_internet_traffic")
    s.index.name = "square_id"
    return s.sort_index()


# ── Time / convenience helpers ────────────────────────────────────────────────
def convert_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Add datetime + calendar features in-place-safe (returns a new frame)."""
    df = df.copy()
    df["datetime"]    = pd.to_datetime(df["time_interval"], unit="ms")
    df["hour"]        = df["datetime"].dt.hour.astype("int8")
    df["day_of_week"] = df["datetime"].dt.dayofweek.astype("int8")
    df["week"]        = df["datetime"].dt.isocalendar().week.astype("int8")
    return df


def get_area_series(df: pd.DataFrame, square_id: int) -> pd.Series:
    """
    Extract the time series for one area from an in-memory DataFrame.

    Expects either (a) the full aggregated frame already filtered to one area,
    or (b) a multi-area frame that we filter here. A 'datetime' column is
    added if missing.
    """
    area_df = df[df["square_id"] == square_id].copy()
    if "datetime" not in area_df.columns:
        area_df["datetime"] = pd.to_datetime(area_df["time_interval"], unit="ms")
    area_df = area_df.sort_values("datetime").set_index("datetime")
    series = area_df["internet_traffic"].astype("float32")
    series.name = f"area_{square_id}"
    return series


def get_top_traffic_area(path_or_df) -> int:
    """
    Return the square_id with the highest total internet traffic.

    Accepts either a path to a Parquet dataset (preferred — streams) or an
    already-loaded DataFrame (legacy notebook signature).
    """
    if isinstance(path_or_df, str):
        totals = total_traffic_per_area(path_or_df)
    else:
        totals = path_or_df.groupby("square_id")["internet_traffic"].sum()
    return int(totals.idxmax())


# ── Legacy compatibility shims ────────────────────────────────────────────────
def save_to_parquet(df: pd.DataFrame, output_path: str) -> None:
    """Single-file save kept for backwards compatibility."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
    size_mb = os.path.getsize(output_path) / (1024 ** 2)
    print(f"Saved to {output_path} ({size_mb:.1f} MB on disk)")


def load_raw_chunk(filepath: str, chunksize: int = 500_000) -> pd.DataFrame:
    """
    Deprecated: kept so older notebooks don't break. New code should call
    `build_parquet_dataset` instead, which streams to disk.

    Aggregates a single raw .txt into memory (sum over country_code).
    """
    dst = filepath + ".tmp.parquet"
    try:
        _aggregate_file_to_parquet(filepath, dst, chunksize=chunksize)
        df = pd.read_parquet(dst)
        return df
    finally:
        if os.path.exists(dst):
            os.remove(dst)


def load_all_raw_files(raw_dir: str, chunksize: int = 500_000) -> pd.DataFrame:
    """
    Deprecated: loads everything into memory. On a 20 GB raw dataset this
    will OOM. Prefer `build_parquet_dataset(raw_dir, out_dir)` followed by
    `load_area_from_parquet(out_dir, [...])`.
    """
    import warnings
    warnings.warn(
        "load_all_raw_files() materialises the full dataset in RAM and is "
        "unsafe at 20 GB scale. Use build_parquet_dataset() + "
        "load_area_from_parquet() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    files = sorted(f for f in os.listdir(raw_dir) if f.endswith(".txt"))
    if not files:
        raise FileNotFoundError(f"No .txt files found in {raw_dir}")

    print(f"Found {len(files)} file(s) to load.\n")
    pieces = []
    for fname in tqdm(files, desc="Loading files"):
        pieces.append(load_raw_chunk(os.path.join(raw_dir, fname), chunksize))

    df = pd.concat(pieces, ignore_index=True)
    mem_after = memory_usage_mb(df)
    print(f"\nLoaded {len(df):,} aggregated rows; in-memory size: {mem_after:.1f} MB")
    return df

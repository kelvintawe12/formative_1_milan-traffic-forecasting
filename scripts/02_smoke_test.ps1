#requires -Version 5.1
<#
.SYNOPSIS
  Run the loader on one daily file to verify the pipeline before the full run.

.DESCRIPTION
  Copies the first .txt in data\raw\ to a temporary one-day directory, runs
  build_parquet_dataset on it, then prints memory/timing stats. Cheap (~30-60s)
  and catches almost all errors that would otherwise blow up four hours into
  the real run.
#>
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPy      = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$RawDir      = Join-Path $ProjectRoot 'data\raw'
$SmokeIn     = Join-Path $ProjectRoot 'data\raw_one_day'
$SmokeOut    = Join-Path $ProjectRoot 'data\processed\smoke'

if (-not (Test-Path $VenvPy)) {
  throw "Virtual environment not found. Run scripts\00_setup_env.ps1 first."
}

$firstTxt = Get-ChildItem -Path $RawDir -Filter '*.txt' | Sort-Object Name | Select-Object -First 1
if (-not $firstTxt) {
  throw "No .txt files found in $RawDir. Run scripts\01_download_data.ps1 first."
}

Write-Host "=== Smoke test on $($firstTxt.Name) ===" -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path $SmokeIn  | Out-Null
New-Item -ItemType Directory -Force -Path $SmokeOut | Out-Null
Copy-Item -Force -Path $firstTxt.FullName -Destination $SmokeIn

& $VenvPy -c @"
import os, sys, time
sys.path.insert(0, r'$ProjectRoot')
from src.data.loader import build_parquet_dataset, load_area_from_parquet, memory_usage_mb

t0 = time.perf_counter()
summary = build_parquet_dataset(r'$SmokeIn', r'$SmokeOut', chunksize=1_000_000)
print()
print(summary.to_string(index=False))
print(f'\\nElapsed: {time.perf_counter()-t0:.1f}s')

# Spot-check: read a single area
df = load_area_from_parquet(r'$SmokeOut', 4159)
print(f'\\nSpot-check (area 4159): {len(df):,} rows, {memory_usage_mb(df):.2f} MB in RAM')
print(df.head())
"@
if ($LASTEXITCODE -ne 0) { throw "Smoke test failed." }

Write-Host ""
Write-Host "Smoke test passed." -ForegroundColor Green
Write-Host "Next: .\scripts\03_run_all.ps1  (this will take several hours)" -ForegroundColor Green

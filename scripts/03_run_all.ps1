#requires -Version 5.1
<#
.SYNOPSIS
  Execute notebooks 01 -> 02 -> 03 -> 04 end-to-end via nbconvert.

.DESCRIPTION
  Delegates to run_pipeline.py at the project root. Use --skip to skip stages
  already done (e.g. -Skip '01' once the Parquet store is built), or -Only to
  run just a subset.

.PARAMETER Skip
  Stage IDs to skip ('01','02','03','04').

.PARAMETER Only
  Stage IDs to run, overriding the default sequence.

.PARAMETER TimeoutSeconds
  Per-cell execution timeout. Default 7200 (2h) -- bump for SARIMA at s=144.
#>
param(
  [string[]]$Skip = @(),
  [string[]]$Only = @(),
  [int]$TimeoutSeconds = 14400
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPy      = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$Driver      = Join-Path $ProjectRoot 'run_pipeline.py'

if (-not (Test-Path $VenvPy)) {
  throw "Virtual environment not found. Run scripts\00_setup_env.ps1 first."
}
if (-not (Test-Path $Driver)) {
  throw "run_pipeline.py not found at $Driver"
}

$args = @($Driver, '--timeout', $TimeoutSeconds)
if ($Skip.Count -gt 0) { $args += @('--skip') + $Skip }
if ($Only.Count -gt 0) { $args += @('--only') + $Only }

Write-Host "=== Running pipeline ===" -ForegroundColor Cyan
Write-Host "python $($args -join ' ')"
Write-Host ""
Write-Host "This is the long one. Plan on:"
Write-Host "  01 (data handling)  ~30-60 min"
Write-Host "  02 (EDA)            ~5-10 min"
Write-Host "  03 (models)         several hours  <- bottleneck (SARIMA s=144)"
Write-Host "  04 (reporting)      ~1 min"
Write-Host ""

& $VenvPy @args
if ($LASTEXITCODE -ne 0) {
  throw "Pipeline failed with exit code $LASTEXITCODE. See output above. Re-run with -Skip to resume after the failed stage."
}

Write-Host ""
Write-Host "Pipeline complete." -ForegroundColor Green
Write-Host "Outputs:" -ForegroundColor Green
Write-Host "  notebooks\*.executed.ipynb       (executed copies of each notebook)" -ForegroundColor Green
Write-Host "  outputs\figures\*.png            (all plots)" -ForegroundColor Green
Write-Host "  outputs\tables\*.csv             (performance + timing tables)" -ForegroundColor Green
Write-Host "  outputs\models\all_results.pkl   (pickled model results)" -ForegroundColor Green

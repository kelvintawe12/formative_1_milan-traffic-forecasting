#requires -Version 5.1
<#
.SYNOPSIS
  One-button driver: setup -> download -> smoke -> run all notebooks.

.DESCRIPTION
  Runs scripts/00..03 in order. Each step is idempotent so re-running is safe.

  Estimated total wall-clock time (CPU only, fast laptop):
    setup     ~2-5 min   (one-time)
    download  ~30-90 min (network-bound, ~20 GB)
    smoke     ~1 min
    run-all   ~4-8 hours (SARIMA at s=144 is the bottleneck)

.PARAMETER SkipDownload
  Skip step 01 (data download). Use if data\raw\ is already populated.

.PARAMETER SkipSmoke
  Skip step 02 (smoke test). Not recommended on first run.

.PARAMETER Cuda
  Install the CUDA build of torch.
#>
param(
  [switch]$SkipDownload,
  [switch]$SkipSmoke,
  [switch]$Cuda
)

$ErrorActionPreference = 'Stop'
$ScriptDir = $PSScriptRoot

function Step($name, $action) {
  Write-Host ""
  Write-Host "########################################" -ForegroundColor Magenta
  Write-Host "##  $name" -ForegroundColor Magenta
  Write-Host "########################################" -ForegroundColor Magenta
  $t0 = Get-Date
  & $action
  $elapsed = (Get-Date) - $t0
  Write-Host ""
  Write-Host "($name took $($elapsed.ToString('hh\:mm\:ss')))" -ForegroundColor DarkGray
}

Step "00 setup env" {
  $args = @{}
  if ($Cuda) { $args['Cuda'] = $true }
  & (Join-Path $ScriptDir '00_setup_env.ps1') @args
}

if (-not $SkipDownload) {
  Step "01 download data" {
    & (Join-Path $ScriptDir '01_download_data.ps1')
  }
} else {
  Write-Host "Skipping 01 download (--SkipDownload)." -ForegroundColor Yellow
}

if (-not $SkipSmoke) {
  Step "02 smoke test" {
    & (Join-Path $ScriptDir '02_smoke_test.ps1')
  }
} else {
  Write-Host "Skipping 02 smoke (--SkipSmoke)." -ForegroundColor Yellow
}

Step "03 run all notebooks" {
  & (Join-Path $ScriptDir '03_run_all.ps1')
}

Write-Host ""
Write-Host "ALL DONE." -ForegroundColor Green

#requires -Version 5.1
<#
.SYNOPSIS
  Download the Milan Telecommunications activity dataset from Harvard Dataverse.

.DESCRIPTION
  Uses the Dataverse public API (no auth, no clicks). Files are streamed one at
  a time into data\raw\, with a SHA size-check to skip already-downloaded files
  on re-runs. If a download fails, just re-run -- it picks up where it stopped.

  The dataset persistent ID is doi:10.7910/DVN/EGZHFV (Milan telecom activity).

.PARAMETER OutDir
  Where to write the extracted .txt files. Default: data\raw\

.PARAMETER MaxParallel
  Number of concurrent downloads. Default 3. Don't push this high -- Dataverse
  rate-limits aggressively.
#>
param(
  [string]$OutDir = $null,
  [int]$MaxParallel = 3
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $ProjectRoot 'data\raw' }
$VenvPy = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $VenvPy)) {
  throw "Virtual environment not found. Run scripts\00_setup_env.ps1 first."
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Section($msg) {
  Write-Host ""
  Write-Host "=== $msg ===" -ForegroundColor Cyan
}

Section "Downloading Milan telecom dataset"
Write-Host "Output directory : $OutDir"
Write-Host "Max parallel     : $MaxParallel"
Write-Host ""

# Delegate to a small Python helper so we have proper HTTP, progress bars, and
# transparent .gz / .tar / .zip handling without reinventing them in PowerShell.
$helper = Join-Path $ProjectRoot 'scripts\_download_dataverse.py'
& $VenvPy $helper --out-dir $OutDir --max-parallel $MaxParallel

# Check if download succeeded
if ($LASTEXITCODE -eq 0) {
  Section "Success"
  Write-Host "Data downloaded successfully!" -ForegroundColor Green
} else {
  Write-Host ""
  Write-Host "Download failed (exit code $LASTEXITCODE)" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "This is likely due to the Harvard Dataverse guestbook requirement." -ForegroundColor Cyan
  Write-Host ""
  Write-Host "SOLUTION:" -ForegroundColor Cyan
  Write-Host "  Read: ..\DATA_DOWNLOAD.md" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "Quick options:" -ForegroundColor Cyan
  Write-Host "  1. Download manually from: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV"
  Write-Host "  2. Use sample data for testing: .\.venv\Scripts\python.exe scripts\generate_sample_data.py 5"
  Write-Host ""
}

Section "Verifying file count"
$count = (Get-ChildItem -Path $OutDir -Filter '*.txt').Count
Write-Host "Found $count .txt file(s) in $OutDir"
if ($count -lt 60) {
  Write-Warning "Expected ~62 daily files (Nov 1 - Dec 31, 2013). Got $count. Re-run this script to retry missing files."
} else {
  Write-Host "Looks good." -ForegroundColor Green
}

Section "Done"
Write-Host "Next: .\scripts\02_smoke_test.ps1" -ForegroundColor Green

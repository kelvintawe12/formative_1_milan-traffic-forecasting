#requires -Version 5.1
<#
.SYNOPSIS
  Create a local Python virtual environment and install all dependencies.

.DESCRIPTION
  - Creates .venv\ in the project root if it doesn't exist.
  - Installs requirements.txt + jupyter + nbconvert.
  - Idempotent: re-running only installs missing/outdated packages.

.PARAMETER Python
  Path to the Python interpreter to use. Defaults to the first `python` on PATH.

.PARAMETER Cuda
  Install the CUDA build of torch instead of the CPU build. Off by default.
#>
param(
  [string]$Python = 'python',
  [switch]$Cuda
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvDir     = Join-Path $ProjectRoot '.venv'

function Section($msg) {
  Write-Host ""
  Write-Host "=== $msg ===" -ForegroundColor Cyan
}

Section "Checking Python"
$pyVersion = & $Python --version 2>&1
if ($LASTEXITCODE -ne 0) {
  throw "Python not found at '$Python'. Install Python 3.10 or 3.11 from python.org and re-run."
}
Write-Host "Found: $pyVersion"

Section "Creating virtual environment"
if (Test-Path $VenvDir) {
  Write-Host ".venv already exists at $VenvDir (re-using)"
} else {
  & $Python -m venv $VenvDir
  if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
  Write-Host "Created $VenvDir"
}

$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path $VenvPy)) { throw "venv python not found at $VenvPy" }

Section "Upgrading pip / wheel"
& $VenvPy -m pip install --upgrade pip wheel setuptools | Out-Host

Section "Installing project dependencies"
$reqPath = Join-Path $ProjectRoot 'requirements.txt'
& $VenvPy -m pip install -r $reqPath | Out-Host
if ($LASTEXITCODE -ne 0) { throw "pip install -r requirements.txt failed" }

if ($Cuda) {
  Section "Installing CUDA build of torch"
  & $VenvPy -m pip install --upgrade `
      --index-url https://download.pytorch.org/whl/cu121 `
      torch | Out-Host
}

Section "Smoke import test"
& $VenvPy -c @"
import sys
mods = ['numpy', 'pandas', 'pyarrow', 'matplotlib', 'seaborn',
        'statsmodels', 'sklearn', 'torch', 'tqdm']
missing = []
for m in mods:
    try:
        __import__(m)
        print(f'  OK  {m}')
    except Exception as e:
        missing.append((m, str(e)))
        print(f'  FAIL {m}: {e}')
if missing:
    sys.exit(1)
"@
if ($LASTEXITCODE -ne 0) { throw "Some modules failed to import." }

Section "Done"
Write-Host "Activate the environment with:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "Or just run the next script (it will use .venv automatically):" -ForegroundColor Green
Write-Host "  .\scripts\01_download_data.ps1" -ForegroundColor Green

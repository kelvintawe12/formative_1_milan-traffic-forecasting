# scripts/

Automation for the full pipeline. PowerShell (`.ps1`) and bash (`.sh`)
versions exist for every step; they do exactly the same thing.

## Single-button run

```powershell
# PowerShell (Windows, native)
.\scripts\run_everything.ps1
```

```bash
# bash (WSL, git-bash, Linux, macOS)
./scripts/run_everything.sh
```

Useful flags:

| PowerShell | bash | Effect |
|---|---|---|
| `-SkipDownload` | `--skip-download` | data/raw already populated |
| `-SkipSmoke` | `--skip-smoke` | skip the one-day dry run |
| `-Cuda` | `--cuda` | install the CUDA build of torch |

Every step is idempotent — re-running picks up where it left off, so if
the network drops mid-download or the laptop reboots you can just re-run.

## Step-by-step (if you want to drive each stage yourself)

| # | PowerShell | bash | What it does | Time |
|---|---|---|---|---|
| 00 | `.\scripts\00_setup_env.ps1` | `./scripts/00_setup_env.sh` | Create `.venv`, install deps | 2–5 min |
| 01 | `.\scripts\01_download_data.ps1` | `./scripts/01_download_data.sh` | Download the ~20 GB dataset via Dataverse API | 30–90 min |
| 02 | `.\scripts\02_smoke_test.ps1` | `./scripts/02_smoke_test.sh` | Run loader on one day | ~1 min |
| 03 | `.\scripts\03_run_all.ps1` | `./scripts/03_run_all.sh` | Execute notebooks 01→04 | 4–8 h |

The download helper is shared: `scripts/_download_dataverse.py` is called
by both `.ps1` and `.sh` so the actual download logic only exists once.

## If the Dataverse API fails

The script will print `FAIL` lines and exit 1. Causes I've seen:

- **Guestbook gate.** Some Dataverse datasets require accepting terms via
  a browser before the API will serve files. If so, open
  <https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV>,
  click *Access Dataset → Terms*, accept, then re-run.
- **Rate limit.** Lower `MAX_PARALLEL` (env var) or `-MaxParallel` to `1`.
- **Server 5xx.** Retry — Dataverse intermittently 502s on large files.
  The script keeps partial files and resumes; just re-run.

## Resuming after a failed pipeline stage

```powershell
# Skip stages that already finished
.\scripts\03_run_all.ps1 -Skip 01,02

# Or run just one stage
.\scripts\03_run_all.ps1 -Only 03
```

```bash
./scripts/03_run_all.sh --skip 01 02
./scripts/03_run_all.sh --only 03
```

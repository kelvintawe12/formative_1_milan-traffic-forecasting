"""
Download the Milan Telecom Big Data Challenge dataset from Harvard Dataverse.

Used by scripts/01_download_data.{ps1,sh}.

The dataset doi:10.7910/DVN/EGZHFV is gated by a Dataverse "guestbook"
(guestbookID 96). Unauthenticated downloads return HTTP 400. The only working
programmatic path is an API token: authenticated downloads have their guestbook
response auto-recorded server-side.

Token setup (one time):
  1. Visit https://dataverse.harvard.edu/loginpage.xhtml and create an account
     or log in (ORCID / GitHub / institutional SSO all work).
  2. Click your name (top right) -> API Token -> Create / Recreate Token.
  3. Set the token in an env var BEFORE running this script:
        PowerShell:   $env:DATAVERSE_API_TOKEN = "your-token-here"
        bash:         export DATAVERSE_API_TOKEN=your-token-here

The script reads the token from $DATAVERSE_API_TOKEN. If unset, it falls back
to anonymous access (which 400s on this dataset and prints clear remediation).

Idempotent: re-run to resume. Failed downloads leave a *.partial file that the
next run overwrites.
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sys
import tarfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import json

DATAVERSE_HOST = "https://dataverse.harvard.edu"
DATASET_DOI    = "doi:10.7910/DVN/EGZHFV"
TOKEN_ENV_VAR  = "DATAVERSE_API_TOKEN"
USER_AGENT     = "milan-traffic-forecasting/1.0"

API_TOKEN = os.environ.get(TOKEN_ENV_VAR, "").strip() or None


# ── HTTP helpers ──────────────────────────────────────────────────────────────
def _open(url: str, timeout: int = 60):
    headers = {"User-Agent": USER_AGENT}
    if API_TOKEN:
        headers["X-Dataverse-key"] = API_TOKEN
    req = Request(url, headers=headers)
    return urlopen(req, timeout=timeout)


def list_files(doi: str) -> list[dict]:
    """Return the list of file descriptors for a dataset."""
    url = (f"{DATAVERSE_HOST}/api/datasets/:persistentId/"
           f"?persistentId={quote(doi, safe=':/')}")
    with _open(url, timeout=60) as resp:
        body = resp.read()
    payload = json.loads(body)
    if payload.get("status") != "OK":
        raise RuntimeError(f"Dataverse API returned status={payload.get('status')}")
    return payload["data"]["latestVersion"]["files"]


def _name_of(file_record: dict) -> str:
    df = file_record["dataFile"]
    label = file_record.get("directoryLabel")
    name  = df.get("filename") or df.get("originalFileName") or f"id_{df['id']}"
    if label:
        return f"{label.replace(os.sep,'/').strip('/').replace('/', '_')}__{name}"
    return name


def _size_of(file_record: dict) -> int:
    return int(file_record["dataFile"].get("filesize", 0) or 0)


# ── Diagnostics ───────────────────────────────────────────────────────────────
def _diagnose_400(err: HTTPError) -> str:
    """Read the JSON body Dataverse returns on a 400 to surface the real cause."""
    try:
        body = err.read()
        msg = json.loads(body).get("message", "")
        return msg[:240] if msg else f"HTTP 400 (no message): {body[:120]!r}"
    except Exception:                                                # noqa: BLE001
        return f"HTTP 400 (unreadable body)"


def _hint_for_guestbook() -> str:
    return (
        "\nThis dataset is guestbook-gated (guestbookID 96). Unauthenticated "
        "downloads return HTTP 400.\n"
        "Fix: get a free Harvard Dataverse API token and set it before retrying.\n"
        "  1. Sign in at https://dataverse.harvard.edu/loginpage.xhtml "
        "(ORCID/GitHub/SSO all work)\n"
        "  2. Click your name (top right) -> API Token -> Create Token\n"
        f"  3. Set the token (env var {TOKEN_ENV_VAR}):\n"
        f"        PowerShell:   $env:{TOKEN_ENV_VAR} = \"<your-token>\"\n"
        f"        bash:         export {TOKEN_ENV_VAR}=<your-token>\n"
        "  4. Re-run scripts\\01_download_data.ps1 (or .sh)\n"
    )


# ── Download + extraction ─────────────────────────────────────────────────────
def download_file(file_record: dict, out_dir: Path, retries: int = 3) -> str:
    df = file_record["dataFile"]
    fid = df["id"]
    name = _name_of(file_record)
    expected_size = _size_of(file_record)

    # Already-extracted .txt? skip
    txt_target = out_dir / Path(name).with_suffix(".txt").name
    if txt_target.exists() and txt_target.stat().st_size > 0:
        return f"SKIP   {name} (extracted already)"

    archive_target = out_dir / name
    if (archive_target.exists()
            and expected_size
            and archive_target.stat().st_size == expected_size):
        _extract(archive_target, out_dir)
        return f"EXTRACT {name}"

    url = f"{DATAVERSE_HOST}/api/access/datafile/{fid}"
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            tmp = archive_target.with_suffix(archive_target.suffix + ".partial")
            with _open(url, timeout=300) as resp, open(tmp, "wb") as fout:
                shutil.copyfileobj(resp, fout, length=1024 * 1024)
            tmp.rename(archive_target)
            _extract(archive_target, out_dir)
            return f"OK     {name} ({archive_target.stat().st_size/1e6:.1f} MB)"
        except HTTPError as e:
            if e.code == 400:
                return f"FAIL   {name}: {_diagnose_400(e)}"
            last_err = f"HTTP {e.code} {e.reason}"
            time.sleep(2 ** attempt)
        except (URLError, TimeoutError) as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
        except Exception as e:                                       # noqa: BLE001
            last_err = str(e)
            break

    return f"FAIL   {name}: {last_err}"


def _extract(path: Path, out_dir: Path) -> None:
    p = str(path).lower()
    if p.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            for member in zf.namelist():
                if member.endswith("/"):
                    continue
                target_name = Path(member).name
                if not target_name:
                    continue
                with zf.open(member) as src, open(out_dir / target_name, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        path.unlink()
    elif p.endswith(".tar") or p.endswith(".tar.gz") or p.endswith(".tgz"):
        mode = "r:gz" if p.endswith((".tar.gz", ".tgz")) else "r"
        with tarfile.open(path, mode) as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                target_name = Path(member.name).name
                if not target_name:
                    continue
                src = tf.extractfile(member)
                if src is None:
                    continue
                with open(out_dir / target_name, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        path.unlink()
    elif p.endswith(".gz"):
        target = out_dir / Path(path.stem).name
        with gzip.open(path, "rb") as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        path.unlink()
    # plain .txt: leave as-is


# ── Driver ────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--filter", default=None,
                        help="Substring filter on filenames (debug only)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if API_TOKEN:
        print(f"Using API token from ${TOKEN_ENV_VAR} (len={len(API_TOKEN)})")
    else:
        print(f"WARNING: no ${TOKEN_ENV_VAR} set. Anonymous downloads will likely "
              "be rejected with HTTP 400 by the dataset's guestbook gate.",
              file=sys.stderr)
        print(_hint_for_guestbook(), file=sys.stderr)

    print(f"\nListing files for {DATASET_DOI} ...")
    try:
        files = list_files(DATASET_DOI)
    except Exception as e:                                           # noqa: BLE001
        print(f"FATAL: could not list dataset files: {e}", file=sys.stderr)
        return 2

    if args.filter:
        files = [f for f in files if args.filter in _name_of(f)]

    total = len(files)
    total_bytes = sum(_size_of(f) for f in files)
    print(f"  {total} file(s), {total_bytes/1e9:.2f} GB total")
    print(f"Downloading with {args.max_parallel} parallel worker(s)...\n")

    ok = 0
    failed: list[str] = []
    saw_guestbook_block = False
    with ThreadPoolExecutor(max_workers=args.max_parallel) as pool:
        futs = {pool.submit(download_file, f, out_dir): f for f in files}
        for i, fut in enumerate(as_completed(futs), 1):
            status = fut.result()
            print(f"[{i:>3}/{total}] {status}")
            if status.startswith("FAIL"):
                failed.append(status)
                if "Guestbook" in status or "guestbook" in status:
                    saw_guestbook_block = True
            else:
                ok += 1

    print(f"\nDone: {ok}/{total} OK, {len(failed)} failed.")
    if failed:
        print("\nFailures (re-run this script to retry):")
        for line in failed[:10]:
            print(" ", line)
        if len(failed) > 10:
            print(f"  ...and {len(failed)-10} more.")
        if saw_guestbook_block:
            print(_hint_for_guestbook(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

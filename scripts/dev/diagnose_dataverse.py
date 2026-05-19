#!/usr/bin/env python3
"""
Diagnose Dataverse API issues for Milan dataset download.
"""

import json
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DATAVERSE_HOST = "https://dataverse.harvard.edu"
DATASET_DOI    = "doi:10.7910/DVN/EGZHFV"
USER_AGENT = "milan-traffic-forecasting/1.0 (+https://github.com/)"

def _open(url: str, timeout: int = 60):
    req = Request(url, headers={"User-Agent": USER_AGENT})
    return urlopen(req, timeout=timeout)

def main():
    print("=== Dataverse API Diagnostic ===\n")
    
    # Step 1: Try to list files
    print("Step 1: Listing dataset files...\n")
    list_url = (f"{DATAVERSE_HOST}/api/datasets/:persistentId/"
                f"?persistentId={quote(DATASET_DOI, safe=':/')}")
    print(f"URL: {list_url}\n")
    
    try:
        with _open(list_url, timeout=60) as resp:
            body = resp.read()
        payload = json.loads(body)
        
        if payload.get("status") != "OK":
            print(f"ERROR: API status = {payload.get('status')}")
            print(f"Response: {json.dumps(payload, indent=2)}")
            return 1
        
        files = payload["data"]["latestVersion"]["files"]
        print(f"✓ Found {len(files)} files\n")
        
        # Show first 3 files
        print("First 3 files:")
        for i, f in enumerate(files[:3]):
            fid = f["dataFile"]["id"]
            fname = f["dataFile"].get("filename") or f["dataFile"].get("originalFileName") or f"id_{fid}"
            fsize = f["dataFile"].get("filesize", 0)
            print(f"  [{i}] ID={fid} (type={type(fid).__name__}), name={fname}, size={fsize}")
        
        # Step 2: Try to construct and test a download URL for the first file
        print(f"\nStep 2: Testing download URL for first file...\n")
        first_file = files[0]
        fid = first_file["dataFile"]["id"]
        fname = first_file["dataFile"].get("filename") or f"file_{fid}"
        
        dl_url = f"{DATAVERSE_HOST}/api/access/datafile/{fid}"
        print(f"URL: {dl_url}\n")
        
        try:
            req = Request(dl_url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=10) as resp:
                print(f"✓ Success! Status: {resp.status}")
                print(f"  Content-Type: {resp.headers.get('Content-Type')}")
                print(f"  Content-Length: {resp.headers.get('Content-Length')}")
                # Read just first 100 bytes to verify it's valid
                data = resp.read(100)
                print(f"  First 100 bytes: {data[:100]}")
        except HTTPError as e:
            print(f"✗ HTTP Error {e.code}: {e.reason}")
            print(f"  URL: {e.url}")
            try:
                error_body = e.read().decode('utf-8')
                print(f"  Response: {error_body[:500]}")
            except:
                pass
        except URLError as e:
            print(f"✗ URL Error: {e.reason}")
        except Exception as e:
            print(f"✗ Error: {type(e).__name__}: {e}")
        
        return 0
        
    except HTTPError as e:
        print(f"✗ HTTP Error {e.code}: {e.reason}")
        print(f"  URL: {e.url}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"  Response: {error_body}")
        except:
            pass
        return 1
    except URLError as e:
        print(f"✗ URL Error: {e.reason}")
        print("  (Check internet connection)")
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ JSON Decode Error: {e}")
        print(f"  Body preview: {body[:500]}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

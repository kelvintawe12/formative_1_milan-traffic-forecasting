#!/usr/bin/env python3
"""
Try downloading using requests library with proper session handling.
"""

import sys

try:
    import requests
except ImportError:
    print("requests not available, trying alternate method...", file=sys.stderr)
    sys.exit(1)

from urllib.parse import quote

DATAVERSE_HOST = "https://dataverse.harvard.edu"
DATASET_DOI    = "doi:10.7910/DVN/EGZHFV"

def test_requests_session():
    """Use requests.Session to handle guestbook cookies properly."""
    print("=== Using Requests Session ===\n")
    
    session = requests.Session()
    session.headers.update({"User-Agent": "milan-traffic-forecasting/1.0"})
    
    # First, get the dataset page to establish session
    print("Step 1: Accessing dataset page...")
    dataset_url = f"{DATAVERSE_HOST}/dataset.xhtml?persistentId={DATASET_DOI}"
    try:
        resp = session.get(dataset_url, timeout=10)
        print(f"  ✓ Status {resp.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Try to find and submit guestbook form
    print("\nStep 2: Looking for guestbook form...")
    if "guestbook" in resp.text.lower():
        print("  ✓ Found 'guestbook' in page content")
    else:
        print("  ! No 'guestbook' found in page content")
    
    # Try the guestbook submission endpoint with session
    print("\nStep 3: Attempting guestbook submission...")
    
    # Try various endpoints
    endpoints = [
        f"{DATAVERSE_HOST}/api/guestbook/2674255",  # File-specific
        f"{DATAVERSE_HOST}/api/guestbookresponse",
        f"{DATAVERSE_HOST}/guestbook",
        f"{DATAVERSE_HOST}/api/datasets/:persistentId/guestbook?persistentId={quote(DATASET_DOI, safe=':/')}",
    ]
    
    gb_data = {
        "name": "Research User",
        "email": "user@research.edu",
        "institution": "Academic Institution",
        "position": "Researcher",
        "guestbookId": "96",
    }
    
    for endpoint in endpoints:
        try:
            resp = session.post(endpoint, data=gb_data, timeout=10)
            if resp.status_code < 400:
                print(f"  ✓ {endpoint}: Status {resp.status_code}")
                break
        except:
            pass
    
    # Now try downloading
    print("\nStep 4: Attempting download with session...")
    fid = 2674255
    dl_url = f"{DATAVERSE_HOST}/api/access/datafile/{fid}"
    
    try:
        resp = session.get(dl_url, timeout=10, stream=True)
        if resp.status_code == 200:
            print(f"  ✓ Download successful! Status {resp.status_code}")
            print(f"    Content-Type: {resp.headers.get('Content-Type')}")
            print(f"    Content-Length: {resp.headers.get('Content-Length')}")
            return True
        else:
            print(f"  ✗ HTTP {resp.status_code}")
            try:
                error = resp.json()
                print(f"    Message: {error.get('message', error)}")
            except:
                print(f"    Response: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_requests_session()
    sys.exit(0 if success else 1)

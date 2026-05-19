#!/usr/bin/env python3
"""
Test different methods to bypass or satisfy Dataverse guestbook requirement.
"""

import json
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import http.cookiejar
import urllib.request

DATAVERSE_HOST = "https://dataverse.harvard.edu"
DATASET_DOI    = "doi:10.7910/DVN/EGZHFV"
USER_AGENT = "milan-traffic-forecasting/1.0 (+https://github.com/)"

def test_method_1_guestbook_api():
    """Test submitting guestbook via API endpoint."""
    print("\n=== Method 1: Guestbook API Endpoint ===\n")
    
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    
    # Try different guestbook submission endpoints
    endpoints = [
        f"{DATAVERSE_HOST}/api/datasets/:persistentId/submitGuestbookResponse?persistentId={quote(DATASET_DOI, safe=':/')}",
        f"{DATAVERSE_HOST}/api/guestbook/96",  # Direct guestbook ID
    ]
    
    for endpoint in endpoints:
        print(f"Trying: {endpoint}")
        gb_data = b"name=User&email=user@test.com&institution=Test&position=Researcher&guestbookId=96"
        try:
            req = Request(endpoint, data=gb_data, headers={"User-Agent": USER_AGENT})
            with opener.open(req, timeout=10) as resp:
                result = resp.read()
                print(f"  ✓ Status {resp.status}")
                print(f"    Response: {result[:200]}")
        except HTTPError as e:
            print(f"  ✗ HTTP {e.code}: {e.reason}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Now try downloading after guestbook submission
    print(f"\nTrying download after submission...")
    fid = 2674255
    dl_url = f"{DATAVERSE_HOST}/api/access/datafile/{fid}"
    try:
        req = Request(dl_url, headers={"User-Agent": USER_AGENT})
        with opener.open(req, timeout=10) as resp:
            print(f"  ✓ Download successful! Status {resp.status}")
            data = resp.read(100)
            print(f"    First 100 bytes: {data}")
    except HTTPError as e:
        print(f"  ✗ HTTP {e.code}: {e.reason}")
        try:
            error = json.loads(e.read().decode())
            print(f"    Message: {error.get('message')}")
        except:
            pass

def test_method_2_guestbook_response_param():
    """Test adding guestbook response as query parameter."""
    print("\n=== Method 2: Query Parameter ===\n")
    
    fid = 2674255
    
    # Try different query parameter formats
    params = [
        f"guestbookResponse=true",
        f"guestbookId=96",
        f"guestbook=1",
    ]
    
    for param in params:
        url = f"{DATAVERSE_HOST}/api/access/datafile/{fid}?{param}"
        print(f"Trying: {url}")
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=10) as resp:
                print(f"  ✓ Download successful! Status {resp.status}")
                data = resp.read(100)
                print(f"    First 100 bytes: {data}")
                return  # Success!
        except HTTPError as e:
            print(f"  ✗ HTTP {e.code}: {e.reason}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

def test_method_3_site_url():
    """Try using direct site download URL instead of API."""
    print("\n=== Method 3: Direct Site Download ===\n")
    
    # Try direct download from dataset page
    urls = [
        f"{DATAVERSE_HOST}/dataset.xhtml?persistentId={DATASET_DOI}",
        f"{DATAVERSE_HOST}/file.xhtml?fileId=2674255",
    ]
    
    for url in urls:
        print(f"Trying: {url[:80]}...")
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=10) as resp:
                print(f"  ✓ Got response, status {resp.status}")
        except Exception as e:
            print(f"  ✗ Error: {type(e).__name__}")

def test_method_4_check_dataset_restrictions():
    """Check dataset metadata for access restrictions."""
    print("\n=== Method 4: Dataset Metadata ===\n")
    
    url = f"{DATAVERSE_HOST}/api/datasets/:persistentId/?persistentId={quote(DATASET_DOI, safe=':/')}"
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        
        dataset = data["data"]["latestVersion"]
        print(f"Dataset: {dataset.get('title', 'N/A')}")
        print(f"Terms of use: {dataset.get('termsOfUse', 'N/A')[:200]}")
        print(f"Restrictions: {dataset.get('restrictionComment', 'N/A')[:200]}")
        print(f"Citation requirement: {dataset.get('citationRequirement', 'N/A')}")
        
        # Check if files have access restrictions
        if dataset.get("files"):
            first_file = dataset["files"][0]
            df = first_file.get("dataFile", {})
            print(f"\nFirst file restrictions: {df.get('restricted', 'N/A')}")
            print(f"First file embargo: {df.get('embargo', 'N/A')}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_method_1_guestbook_api()
    test_method_2_guestbook_response_param()
    test_method_3_site_url()
    test_method_4_check_dataset_restrictions()

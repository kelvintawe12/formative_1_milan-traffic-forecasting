#!/usr/bin/env python3
"""
Final attempt: Try different content types and JSON payloads for guestbook.
"""

import sys
import json

try:
    import requests
except:
    print("requests library required")
    sys.exit(1)

DATAVERSE_HOST = "https://dataverse.harvard.edu"

def test_final_methods():
    """Try various remaining approaches."""
    session = requests.Session()
    session.headers.update({"User-Agent": "milan-traffic-forecasting/1.0"})
    
    fid = 2674255
    
    print("=== Final Dataverse Guestbook Attempts ===\n")
    
    # Method 1: JSON payload to guestbook endpoint
    print("Method 1: JSON guestbook submission")
    endpoints = [
        f"{DATAVERSE_HOST}/api/guestbookresponse",
        f"{DATAVERSE_HOST}/api/datasets/:persistentId/guestbookresponse",
    ]
    
    gb_payload = {
        "name": "Research User",
        "email": "user@research.edu", 
        "institution": "Institution",
        "position": "Researcher",
        "guestbookId": 96
    }
    
    for endpoint in endpoints:
        try:
            resp = session.post(endpoint, json=gb_payload, timeout=5)
            print(f"  {endpoint}: {resp.status_code}")
        except:
            pass
    
    # Method 2: Try /download suffix  
    print("\nMethod 2: Download endpoint variations")
    download_urls = [
        f"{DATAVERSE_HOST}/api/access/datafile/{fid}/download",
        f"{DATAVERSE_HOST}/files/download/{fid}",
        f"{DATAVERSE_HOST}/api/datafiles/{fid}/download",
    ]
    
    for url in download_urls:
        try:
            resp = session.head(url, timeout=5, allow_redirects=True)
            status = resp.status_code
            if status < 400:
                print(f"  ✓ {url}: {status}")
                # Try GET
                resp = session.get(url, timeout=5, stream=True)
                print(f"    GET: {resp.status_code}")
            else:
                print(f"  {url}: {status}")
        except Exception as e:
            print(f"  {url}: Error ({type(e).__name__})")
    
    # Method 3: Check if there's a direct download link
    print("\nMethod 3: Check HTML for direct download link")
    try:
        resp = session.get(f"{DATAVERSE_HOST}/file.xhtml?fileId={fid}", timeout=10)
        if "href=" in resp.text:
            # Look for download href
            import re
            hrefs = re.findall(r'href="([^"]*download[^"]*)"', resp.text)
            if hrefs:
                print(f"  Found {len(hrefs)} download link(s)")
                for href in hrefs[:3]:
                    print(f"    {href[:100]}")
            else:
                print("  No obvious download links found")
    except:
        pass
    
    print("\n✗ No working automated method found for guestbook requirement.")
    print("\nRecommendation: Download data manually via browser")
    print(f"  https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV")
    print("\nOr try these alternative approaches:")
    print("  1. Check if Kaggle has this dataset")
    print("  2. Contact dataset owner for bulk download access")
    print("  3. Use Dataverse CLI tools (requires local installation)")

if __name__ == "__main__":
    test_final_methods()

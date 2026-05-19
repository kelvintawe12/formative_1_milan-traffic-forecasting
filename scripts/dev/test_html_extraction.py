#!/usr/bin/env python3
"""
Try to extract guestbook form from HTML and submit properly.
"""

import sys
import re

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("requests or BeautifulSoup not available", file=sys.stderr)
    # Fallback: try with just requests
    import requests

DATAVERSE_HOST = "https://dataverse.harvard.edu"

def test_html_form():
    """Extract guestbook form from HTML and try submission."""
    print("=== Extracting Guestbook Form ===\n")
    
    session = requests.Session()
    session.headers.update({"User-Agent": "milan-traffic-forecasting/1.0"})
    
    # Get dataset page
    dataset_url = f"{DATAVERSE_HOST}/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV"
    print(f"Fetching {dataset_url}...")
    resp = session.get(dataset_url, timeout=10)
    print(f"Status: {resp.status_code}\n")
    
    html = resp.text
    
    # Look for form elements
    print("Looking for forms in HTML...")
    form_pattern = r'<form[^>]*>(.*?)</form>'
    forms = re.findall(form_pattern, html, re.DOTALL | re.IGNORECASE)
    print(f"Found {len(forms)} form(s)\n")
    
    # Look for guestbook-related content
    if 'guestbook' in html.lower():
        print("✓ Found 'guestbook' in HTML")
        # Extract relevant section
        gb_match = re.search(r'.{200}guestbook.{200}', html, re.IGNORECASE | re.DOTALL)
        if gb_match:
            print(f"Context: ...{gb_match.group()[:300]}...\n")
    else:
        print("! No 'guestbook' found in HTML\n")
    
    # Look for download URLs
    print("Looking for download patterns...")
    download_patterns = [
        r'href=["\']([^"\']*download[^"\']*)["\']',
        r'href=["\']([^"\']*access[^"\']*)["\']',
        r'data-uri=["\']([^"\']*)["\']',
    ]
    
    for pattern in download_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            print(f"\nPattern: {pattern}")
            for match in matches[:3]:
                print(f"  {match[:100]}")

if __name__ == "__main__":
    test_html_form()

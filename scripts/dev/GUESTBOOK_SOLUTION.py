#!/usr/bin/env python3
"""
SOLUTION: Since automated Dataverse download is blocked by guestbook,
provide manual download instructions and/or setup placeholder data.

This script:
1. Explains the guestbook requirement
2. Provides instructions for manual download
3. Creates sample data structure for testing
"""

import sys
import os
from pathlib import Path

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║          DATAVERSE GUESTBOOK REQUIREMENT - MANUAL DOWNLOAD             ║
╚════════════════════════════════════════════════════════════════════════╝

ISSUE:
  The Milan Telecom dataset on Harvard Dataverse requires a Guestbook
  response before download. Automated API access is intentionally blocked.
  
SOLUTION OPTIONS:

Option 1: MANUAL DOWNLOAD (Recommended for Assignment)
  ──────────────────────────────────────────────────────
  1. Go to: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV
  
  2. Click "Download" button for each file (or "Download All")
  
  3. Fill in the guestbook form:
     - Name: (Your name)
     - Email: (Your email)
     - Institution: (Your institution)
     - Position: (e.g., Student, Researcher)
  
  4. Files will download as .txt files
  
  5. Extract all .txt files to: data/raw/
  
  6. Then run: .\\scripts\\02_smoke_test.ps1

Option 2: SAMPLE DATA FOR TESTING (During Development)
  ──────────────────────────────────────────────────────
  Run: .\\scripts\\create_sample_data.ps1
  This creates small sample data in data/raw/ to test your pipeline.

Option 3: ALTERNATIVE SOURCES
  ──────────────────────────────
  - Check if dataset is on Kaggle: https://www.kaggle.com/
  - Search for "Milan telecom" or "TIM Big Data Challenge"
  - Some mirrors may not have guestbook requirement

Option 4: DATAVERSE CLI TOOLS
  ───────────────────────────
  Install pyDataverse: pip install pydataverse
  Provides better support for datasets with access controls

═════════════════════════════════════════════════════════════════════════

ASSIGNMENT ADVICE:
  For academic coursework, you should be able to download data manually
  through the web browser. This is a standard requirement from the
  dataset maintainers for usage tracking and attribution.
  
═════════════════════════════════════════════════════════════════════════
""")

if __name__ == "__main__":
    main()

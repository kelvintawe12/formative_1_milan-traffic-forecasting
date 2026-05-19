#!/usr/bin/env python3
"""
Generate sample Milan traffic data for pipeline testing.
Creates a few small sample files with the same format as the real data.
"""

import os
import random
from pathlib import Path

def generate_sample_data(out_dir: str = "data/raw", num_files: int = 3):
    """
    Generate sample data files matching the real format.
    
    Real format: 8 columns (tab-separated)
    (square_id, time_interval, country_code, sms_in, sms_out, call_in, call_out, internet_traffic)
    
    We generate:
    - 3 days worth (configurable)
    - ~10,000 rows per day (realistic for Milan grid)
    - Realistic value ranges
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {num_files} sample data files in {out_dir}...\n")
    
    # Parameters
    num_squares = 100  # Out of ~10,000 in real data
    country_codes = ["IT", "AT", "CH", "FR", "DE", "SI"]
    rows_per_file = 5000  # ~10x smaller than real
    
    # Generate files
    for day in range(1, num_files + 1):
        filename = f"sms-call-internet-mi-2013-11-{day:02d}.txt"
        filepath = out_path / filename
        
        print(f"  [{day}/{num_files}] {filename} ... ", end="", flush=True)
        
        with open(filepath, 'w') as f:
            for row_idx in range(rows_per_file):
                square_id = random.randint(1, num_squares)
                time_interval = random.randint(0, 95)  # 96 15-min intervals per day
                country_code = random.choice(country_codes)
                sms_in = random.randint(0, 1000)
                sms_out = random.randint(0, 1000)
                call_in = random.randint(0, 500)
                call_out = random.randint(0, 500)
                # Internet traffic: either 0 or realistic value
                internet_traffic = random.randint(0, 10000000) if random.random() > 0.3 else 0
                
                line = f"{square_id}\t{time_interval}\t{country_code}\t{sms_in}\t{sms_out}\t{call_in}\t{call_out}\t{internet_traffic}\n"
                f.write(line)
        
        # Show file size
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"{size_mb:.1f} MB")
    
    total_size = sum(f.stat().st_size for f in out_path.glob("*.txt")) / (1024 * 1024)
    print(f"\n✓ Generated {num_files} files, {total_size:.1f} MB total")
    print(f"  Location: {out_path.resolve()}")
    print(f"\nYou can now test your pipeline with:")
    print(f"  .\\scripts\\02_smoke_test.ps1")

if __name__ == "__main__":
    import sys
    num_files = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    generate_sample_data(num_files=num_files)

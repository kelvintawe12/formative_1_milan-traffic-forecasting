# Data Download Guide

## Issue: Dataverse Guestbook Requirement

The Milan Telecom dataset from Harvard Dataverse (doi:10.7910/DVN/EGZHFV) requires a **Guestbook response** before allowing downloads. This is intentional - the dataset maintainers use this to track usage and require attribution.

**Error seen**: `HTTP 400: You may not download this file without the required Guestbook response for guestbookID 96.`

---

## ✅ Solution 1: Download Manually (Quickest)

### For the Assignment:

1. **Visit the dataset**: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV

2. **Click "Download All"** or select individual files

3. **Fill the Guestbook form**:
   - Name: (Your name)
   - Email: (Your email address)
   - Institution: (Your university/institution)
   - Position: (e.g., "Student", "Researcher")

4. **Download completes**: You'll receive ~62 files (one per day, Nov-Dec 2013)

5. **Extract to folder**:
   ```powershell
   # Extract all .txt files to data/raw/
   Move-Item .\Downloads\*.txt .\data\raw\
   ```

6. **Verify and run pipeline**:
   ```powershell
   .\scripts\02_smoke_test.ps1   # Verify setup
   .\scripts\03_run_all.ps1      # Run full pipeline
   ```

---

## ✅ Solution 2: Use Sample Data (For Testing)

If you want to **test your pipeline** without the 20GB download:

```powershell
# Generate 5 sample data files (~0.7 MB)
.\.venv\Scripts\python.exe scripts/generate_sample_data.py 5

# Now test your pipeline
.\scripts\02_smoke_test.ps1
.\scripts\01_data_handling.ps1   # Run first notebook
```

The sample data has the correct format but is ~100x smaller for quick iteration.

---

## ✅ Solution 3: Alternative Sources

Look for mirrors of this dataset:
- **Kaggle**: Search "Milan telecom" or "TIM Big Data Challenge"
- Some versions may not have guestbook restrictions

---

## ❌ Why Automated Download Failed

Tested approaches that **don't work**:
- ❌ Direct API access (`/api/access/datafile/{id}`)
- ❌ API guestbook endpoints (`/api/guestbook/...`)
- ❌ Session cookies or query parameters
- ❌ HTML form extraction

**Why**: Harvard Dataverse intentionally blocks programmatic access to datasets with guestbooks to ensure proper attribution and usage tracking. This is by design.

---

## 📋 Attribution Required

If you use this dataset, cite it as:

> Telecom Italia (2015). SMS, Call and Internet activity. Harvard Dataverse.  
> https://doi.org/10.7910/DVN/EGZHFV

---

## File Format Reference

Each `.txt` file contains tab-separated data:

```
square_id | time_interval | country_code | sms_in | sms_out | call_in | call_out | internet_traffic
```

Example row:
```
1234	42	IT	145	132	87	92	5432100
```

The pipeline (Task 1) keeps only: `(square_id, time_interval, internet_traffic)` summed by country.

---

## Next Steps

1. Choose Solution 1 or 2 above
2. Run the pipeline:
   ```powershell
   .\scripts\03_run_all.ps1
   ```
3. Open notebooks to explore results:
   ```powershell
   jupyter lab  # Then navigate to notebooks/
   ```

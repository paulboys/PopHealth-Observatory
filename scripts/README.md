# Scripts Directory

Utility scripts for data management and maintenance.

## BRFSS Data Management

### `fetch_brfss_data.py`

Downloads the full BRFSS (Behavioral Risk Factor Surveillance System) dataset from the CDC API and saves it as a compressed Parquet file for offline use in the Streamlit app.

**When to run:**
- Initial setup (before first app launch)
- Quarterly updates (when CDC releases new BRFSS data)
- After API changes or data format updates

**Usage:**

```bash
# Ensure pophealth_observatory environment is activated
conda activate pophealth_observatory

# Run the download script
python scripts/fetch_brfss_data.py
```

**Output:**
- Creates: `data/processed/brfss_indicators.parquet`
- Size: ~3-10 MB (compressed)
- Contains: All BRFSS indicators from 2011-present

**Benefits:**
- ✅ Blazing fast app load times (milliseconds vs seconds)
- ✅ Works offline
- ✅ No API rate limits
- ✅ Consistent data across sessions

**Note:** The generated Parquet file is safe to commit to Git (well under GitHub's 100 MB limit).

#!/usr/bin/env python
"""
Fetch and cache BRFSS data from CDC API to local Parquet file.

This script downloads the full BRFSS Nutrition, Physical Activity, and Obesity
dataset from the CDC's Socrata API and saves it as a compressed Parquet file
for fast, offline access in the Streamlit app.

Run this script periodically (e.g., quarterly) to update the local data cache
when new BRFSS data is released.

Usage:
    python scripts/fetch_brfss_data.py

SPDX-License-Identifier: MIT
"""

import sys
from pathlib import Path

import pandas as pd
import requests


def fetch_brfss_raw_data(limit: int = 150000, timeout: int = 60) -> pd.DataFrame:
    """
    Fetch raw BRFSS data from CDC API.

    Parameters
    ----------
    limit : int
        Maximum number of records to fetch
    timeout : int
        Request timeout in seconds

    Returns
    -------
    pd.DataFrame
        Raw BRFSS data with all columns
    """
    url = f"https://data.cdc.gov/resource/hn4x-zwk7.json?$limit={limit}"

    print("Fetching BRFSS data from CDC API...")
    print(f"URL: {url}")

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()

        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected API response format (not a list)")

        df = pd.DataFrame(data)
        print(f"✓ Successfully fetched {len(df):,} records")
        print(f"✓ Columns: {', '.join(df.columns.tolist())}")

        return df

    except requests.exceptions.RequestException as e:
        print(f"✗ API request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)


def save_to_parquet(df: pd.DataFrame, output_path: Path) -> None:
    """
    Save DataFrame to compressed Parquet file.

    Parameters
    ----------
    df : pd.DataFrame
        Data to save
    output_path : Path
        Destination file path
    """
    # Create directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving to {output_path}...")

    # Save with compression for smaller file size
    df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)

    # Report file size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Saved {len(df):,} records to Parquet file")
    print(f"✓ File size: {size_mb:.2f} MB")


def main():
    """Main execution function."""
    print("=" * 70)
    print("BRFSS Data Download Script")
    print("=" * 70)

    # Define paths
    repo_root = Path(__file__).parent.parent
    output_path = repo_root / "data" / "processed" / "brfss_indicators.parquet"

    # Fetch data
    df = fetch_brfss_raw_data()

    # Display summary statistics
    print("\nData Summary:")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")
    if "yearstart" in df.columns:
        years = sorted(df["yearstart"].unique())
        print(f"  Years: {years[0]} - {years[-1]}")
    if "class" in df.columns:
        n_classes = df["class"].nunique()
        print(f"  Indicator Classes: {n_classes}")
    if "question" in df.columns:
        n_questions = df["question"].nunique()
        print(f"  Unique Questions: {n_questions}")

    # Save to Parquet
    save_to_parquet(df, output_path)

    print("\n" + "=" * 70)
    print("✓ Download complete! The Streamlit app will now use this local file.")
    print("=" * 70)


if __name__ == "__main__":
    main()

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

import logging
import sys
from pathlib import Path

import pandas as pd
import requests

from pophealth_observatory.logging_config import configure_logging, log_with_fallback

logger = logging.getLogger(__name__)


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

    log_with_fallback(logger, logging.INFO, "Fetching BRFSS data from CDC API...")
    log_with_fallback(logger, logging.INFO, f"URL: {url}")

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()

        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected API response format (not a list)")

        df = pd.DataFrame(data)
        log_with_fallback(logger, logging.INFO, f"Successfully fetched {len(df):,} records")
        log_with_fallback(logger, logging.INFO, f"Columns: {', '.join(df.columns.tolist())}")

        return df

    except requests.exceptions.RequestException as e:
        log_with_fallback(logger, logging.ERROR, f"API request failed: {e}")
        sys.exit(1)
    except Exception as e:
        log_with_fallback(logger, logging.ERROR, f"Unexpected error: {e}")
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

    log_with_fallback(logger, logging.INFO, f"Saving to {output_path}...")

    # Save with compression for smaller file size
    df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)

    # Report file size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    log_with_fallback(logger, logging.INFO, f"Saved {len(df):,} records to Parquet file")
    log_with_fallback(logger, logging.INFO, f"File size: {size_mb:.2f} MB")


def main():
    """Main execution function."""
    configure_logging()
    log_with_fallback(logger, logging.INFO, "=" * 70)
    log_with_fallback(logger, logging.INFO, "BRFSS Data Download Script")
    log_with_fallback(logger, logging.INFO, "=" * 70)

    # Define paths
    repo_root = Path(__file__).parent.parent
    output_path = repo_root / "data" / "processed" / "brfss_indicators.parquet"

    # Fetch data
    df = fetch_brfss_raw_data()

    # Display summary statistics
    log_with_fallback(logger, logging.INFO, "Data Summary:")
    log_with_fallback(logger, logging.INFO, f"  Rows: {len(df):,}")
    log_with_fallback(logger, logging.INFO, f"  Columns: {len(df.columns)}")
    if "yearstart" in df.columns:
        years = sorted(df["yearstart"].unique())
        log_with_fallback(logger, logging.INFO, f"  Years: {years[0]} - {years[-1]}")
    if "class" in df.columns:
        n_classes = df["class"].nunique()
        log_with_fallback(logger, logging.INFO, f"  Indicator Classes: {n_classes}")
    if "question" in df.columns:
        n_questions = df["question"].nunique()
        log_with_fallback(logger, logging.INFO, f"  Unique Questions: {n_questions}")

    # Save to Parquet
    save_to_parquet(df, output_path)

    log_with_fallback(logger, logging.INFO, "=" * 70)
    log_with_fallback(logger, logging.INFO, "Download complete! The Streamlit app will now use this local file.")
    log_with_fallback(logger, logging.INFO, "=" * 70)


if __name__ == "__main__":
    main()

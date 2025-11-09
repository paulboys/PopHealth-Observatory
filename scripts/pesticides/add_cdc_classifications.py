#!/usr/bin/env python
"""Add authoritative chemical classifications from CDC Fourth National Report.

This script:
1. Loads pesticide_reference_minimal.csv (our working reference)
2. Loads CDC Fourth Report classification data
3. Matches analytes using CAS numbers (primary) and names (fallback)
4. Adds chemical_class and classification_source columns
5. Saves enriched reference as pesticide_reference_classified.csv

The chemical classifications come from the CDC's Fourth National Report on Human
Exposure to Environmental Chemicals, specifically the pesticide biomonitoring tables.

Usage:
    python scripts/add_cdc_classifications.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MINIMAL_REF = ROOT / "data" / "reference" / "minimal" / "pesticide_reference_minimal.csv"
CDC_CLASSES = ROOT / "data" / "raw" / "cdc" / "fourth_report_pesticide_classes.csv"
OUTPUT_REF = ROOT / "data" / "reference" / "classified" / "pesticide_reference_classified.csv"


def load_minimal_reference(path: Path) -> pd.DataFrame:
    """Load the minimal reference file."""
    df = pd.read_csv(path)
    print(f"Loaded minimal reference: {len(df)} analytes")
    print(f"  With CAS: {df['cas_rn'].notna().sum()}")
    print(f"  Without CAS: {df['cas_rn'].isna().sum()}")
    return df


def load_cdc_classifications(path: Path) -> pd.DataFrame:
    """Load CDC Fourth Report chemical classifications."""
    df = pd.read_csv(path)
    print(f"\nLoaded CDC classifications: {len(df)} chemicals")
    print(f"  Classes: {df['chemical_class'].nunique()} unique")
    print(f"  Subclasses: {df['chemical_subclass'].nunique()} unique")
    return df


def match_by_cas(minimal_df: pd.DataFrame, cdc_df: pd.DataFrame) -> pd.DataFrame:
    """Match analytes to CDC classifications using CAS numbers.

    Returns:
        DataFrame with chemical_class, chemical_subclass, classification_source columns added
    """
    # Create a lookup dictionary from CDC data
    cdc_lookup = {}
    for _, row in cdc_df.iterrows():
        cas = str(row["cas_rn"]).strip()
        cdc_lookup[cas] = {
            "chemical_class": row["chemical_class"],
            "chemical_subclass": row["chemical_subclass"],
            "classification_source": row["data_source"],
        }

    # Add classification columns
    minimal_df["chemical_class"] = ""
    minimal_df["chemical_subclass"] = ""
    minimal_df["classification_source"] = ""

    # Match by CAS number
    matches = 0
    for idx, row in minimal_df.iterrows():
        cas = str(row["cas_rn"]).strip()
        if pd.notna(row["cas_rn"]) and cas in cdc_lookup:
            minimal_df.loc[idx, "chemical_class"] = cdc_lookup[cas]["chemical_class"]
            minimal_df.loc[idx, "chemical_subclass"] = cdc_lookup[cas]["chemical_subclass"]
            minimal_df.loc[idx, "classification_source"] = cdc_lookup[cas]["classification_source"]
            matches += 1

    print(f"\nMatched {matches}/{len(minimal_df)} analytes by CAS number")
    return minimal_df


def main():
    ap = argparse.ArgumentParser(description="Add CDC chemical classifications to minimal reference")
    ap.add_argument("--minimal", default=str(MINIMAL_REF), help="Input minimal reference CSV")
    ap.add_argument("--cdc", default=str(CDC_CLASSES), help="CDC classification CSV")
    ap.add_argument("--output", default=str(OUTPUT_REF), help="Output classified reference CSV")
    args = ap.parse_args()

    print("=" * 70)
    print("CDC Fourth Report Chemical Classification Enrichment")
    print("=" * 70)

    # Load data
    minimal_df = load_minimal_reference(Path(args.minimal))
    cdc_df = load_cdc_classifications(Path(args.cdc))

    # Match by CAS number
    enriched_df = match_by_cas(minimal_df, cdc_df)

    # Save enriched reference
    output_path = Path(args.output)
    enriched_df.to_csv(output_path, index=False)

    print(f"\nSaved enriched reference: {output_path}")

    # Statistics
    classified = enriched_df["chemical_class"].ne("").sum()
    unclassified = enriched_df["chemical_class"].eq("").sum()

    print("\n" + "=" * 70)
    print("Classification Statistics")
    print("=" * 70)
    print(f"  Total analytes: {len(enriched_df)}")
    print(f"  Classified: {classified} ({classified/len(enriched_df)*100:.1f}%)")
    print(f"  Unclassified: {unclassified} ({unclassified/len(enriched_df)*100:.1f}%)")

    if classified > 0:
        print("\nChemical class distribution:")
        class_counts = enriched_df[enriched_df["chemical_class"] != ""]["chemical_class"].value_counts()
        for chem_class, count in class_counts.items():
            print(f"  {chem_class}: {count}")


if __name__ == "__main__":
    main()

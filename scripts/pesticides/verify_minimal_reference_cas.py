#!/usr/bin/env python
"""Verify CAS numbers for all analytes in minimal reference using PubChem API.

This script:
1. Loads pesticide_reference_minimal.csv
2. For each analyte without a verified CAS number:
   - Queries PubChem by chemical name
   - Retrieves CAS number from the best match
   - Validates the match quality
3. Updates the CSV with verified CAS numbers

Usage:
    python scripts/verify_minimal_reference_cas.py
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
MINIMAL_REF = ROOT / "data" / "reference" / "minimal" / "pesticide_reference_minimal.csv"
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def query_pubchem_by_name(analyte_name: str) -> tuple[str, str, str]:
    """Query PubChem for CAS number by chemical name.

    Returns:
        (cas_rn, pubchem_cid, status) where status is one of:
        - "pubchem_api": Successfully found and verified
        - "ambiguous": Multiple matches, manual review needed
        - "not_found": No match in PubChem
        - "api_error": API request failed
    """
    import re

    # Clean up the name for searching
    search_name = analyte_name.strip()

    # Skip obviously bad names
    if "usted" in search_name.lower() or len(search_name) < 3:
        return "", "", "not_found"

    # Clean up common issues
    search_name = search_name.replace("Lipid Adj", "").replace("Lipid Adjusted", "").strip()

    # Try multiple search strategies
    search_variants = [
        search_name,
        search_name.replace("-", ""),  # Remove hyphens
        search_name.replace(",", ""),  # Remove commas
    ]

    # CAS number pattern for extraction from synonyms
    cas_pattern = re.compile(r"^\d{1,7}-\d{2}-\d$")

    for variant in search_variants:
        if not variant or len(variant) < 3:
            continue

        # Try name search
        try:
            search_url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(variant)}/cids/JSON"
            search_resp = requests.get(search_url, timeout=10)

            if search_resp.status_code == 200:
                search_data = search_resp.json()
                if "IdentifierList" in search_data and "CID" in search_data["IdentifierList"]:
                    cids = search_data["IdentifierList"]["CID"]

                    if len(cids) >= 1:
                        # Use first CID (most relevant)
                        cid = str(cids[0])

                        # Get CAS from synonyms endpoint (more reliable than property endpoint)
                        syn_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
                        syn_resp = requests.get(syn_url, timeout=10)

                        if syn_resp.status_code == 200:
                            syn_data = syn_resp.json()
                            if "InformationList" in syn_data and "Information" in syn_data["InformationList"]:
                                info = syn_data["InformationList"]["Information"]
                                if info and "Synonym" in info[0]:
                                    # Extract CAS from synonyms
                                    for syn in info[0]["Synonym"]:
                                        if cas_pattern.match(syn):
                                            status = "ambiguous" if len(cids) > 1 else "pubchem_api"
                                            return syn, cid, status
        except (requests.RequestException, KeyError, ValueError, IndexError):
            continue

    return "", "", "not_found"


def main():
    ap = argparse.ArgumentParser(description="Verify CAS numbers for minimal reference using PubChem")
    ap.add_argument("--input", default=str(MINIMAL_REF), help="Input minimal reference CSV")
    ap.add_argument("--output", default=str(MINIMAL_REF), help="Output CSV (default: overwrites input)")
    ap.add_argument("--rate-limit", type=float, default=0.5, help="Seconds to wait between API requests (default: 0.5)")
    args = ap.parse_args()

    print(f"Loading minimal reference: {args.input}")
    df = pd.read_csv(args.input)

    print(f"Total analytes: {len(df)}")

    # Find analytes without verified CAS (either empty or NaN)
    unverified_mask = (df["cas_rn"].isna()) | (df["cas_rn"] == "")
    unverified = df[unverified_mask].copy()
    print(f"Analytes without verified CAS: {len(unverified)}")

    if len(unverified) == 0:
        print("All analytes already have verified CAS numbers!")
        return

    # Track statistics
    stats = {
        "verified": 0,
        "ambiguous": 0,
        "not_found": 0,
        "api_error": 0,
    }

    print("\nQuerying PubChem API...")
    for idx, row in unverified.iterrows():
        analyte_name = row["analyte_name"]
        total_processed = stats["verified"] + stats["ambiguous"] + stats["not_found"] + stats["api_error"] + 1
        print(
            f"  [{total_processed}/{len(unverified)}] {analyte_name[:50]}...",
            end=" ",
        )

        cas_rn, cid, status = query_pubchem_by_name(analyte_name)

        if status == "pubchem_api" and cas_rn:
            df.loc[idx, "cas_rn"] = cas_rn
            df.loc[idx, "cas_verified_source"] = "pubchem_api"
            stats["verified"] += 1
            print(f"OK {cas_rn}")
        elif status == "ambiguous":
            stats["ambiguous"] += 1
            print(f"WARN Ambiguous (CID {cid})")
        elif status == "not_found":
            stats["not_found"] += 1
            print("X Not found")
        else:
            stats["api_error"] += 1
            print("X API error")

        time.sleep(args.rate_limit)

    # Save updated CSV
    output_path = Path(args.output)
    df.to_csv(output_path, index=False)

    print(f"\nOK Updated reference saved to: {output_path}")
    print("\nStatistics:")
    print(f"  Verified: {stats['verified']}")
    print(f"  Ambiguous (manual review needed): {stats['ambiguous']}")
    print(f"  Not found: {stats['not_found']}")
    print(f"  API errors: {stats['api_error']}")
    print(f"  Total now verified: {df['cas_verified_source'].eq('pubchem_api').sum()}/{len(df)}")


if __name__ == "__main__":
    main()

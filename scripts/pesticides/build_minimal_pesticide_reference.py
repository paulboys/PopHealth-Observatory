#!/usr/bin/env python
"""
Build minimal pesticide reference from verified sources only.

Sources:
1. nhanes_pesticide_variables_discovered.csv - NHANES variable metadata
2. pesticide_reference_curated.csv - PubChem-verified CAS numbers

Output: pesticide_reference_minimal.csv with ONLY directly observable fields.

NO AI-derived classifications. NO inferred parent relationships.
Only: analyte names, verified CAS, matrix, units, cycle ranges from NHANES.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
# Updated structured paths after directory cleanup
DISCOVERED = ROOT / "data" / "reference" / "discovery" / "nhanes_pesticide_variables_discovered.csv"
CURATED = ROOT / "data" / "reference" / "legacy" / "pesticide_reference_curated.csv"
OUTPUT = ROOT / "data" / "reference" / "minimal" / "pesticide_reference_minimal.csv"


def infer_matrix(data_file_name: str, variable_description: str) -> str:
    """Infer matrix from data file naming patterns and descriptions.

    Serum files: PSTPOL, SSPST, POC, PCB, etc.
    Urine files: Most others, especially those with ug/L units
    """
    df_lower = data_file_name.lower()
    desc_lower = variable_description.lower()

    if "pstpol" in df_lower or "sspst" in df_lower or "poc" in df_lower:
        return "serum"
    if "lipid" in desc_lower or "ng/g" in desc_lower or "pg/g" in desc_lower:
        return "serum"
    if "ug/l" in desc_lower.replace(" ", ""):
        return "urine"

    return "unknown"


def extract_unit(variable_description: str) -> str:
    """Extract measurement unit from variable description."""
    desc = variable_description.lower()

    # Common patterns
    if "(ug/l)" in desc:
        return "ug/L"
    if "(ng/g)" in desc:
        return "ng/g"
    if "(pg/g)" in desc:
        return "pg/g"
    if "(mg/dl)" in desc:
        return "mg/dL"

    return ""


def normalize_analyte_name(variable_description: str) -> str:
    """Normalize analyte name from variable description.

    Remove units, extract core chemical name.
    """
    # Remove common suffixes
    desc = variable_description.strip()

    # Remove unit patterns
    for pattern in [
        "(ug/L)",
        "(ng/g)",
        "(pg/g)",
        "(mg/dL)",
        " result",
        " Lipid Adj",
        " Lipid Adjusted",
        "Lipid Adj",
        "Lipid Adjusted",
    ]:
        desc = desc.replace(pattern, "")

    desc = desc.strip()

    # Remove trailing unit-like phrases
    if " (" in desc:
        desc = desc.split(" (")[0].strip()

    return desc


def _normalize_for_matching(s: str) -> str:
    """Normalize strings for fuzzy matching (lowercase alphanumerics only)."""
    import re

    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    ap = argparse.ArgumentParser(description="Build minimal pesticide reference with zero AI inference")
    ap.add_argument("--output", default=str(OUTPUT), help="Output CSV path")
    args = ap.parse_args()

    print(f"Loading NHANES variable discovery data: {DISCOVERED}")
    df_disc = pd.read_csv(DISCOVERED)

    print(f"Loading PubChem-curated CAS numbers: {CURATED}")
    if not CURATED.exists():
        print(f"Warning: {CURATED} not found. Proceeding without verified CAS.")
        df_curated = pd.DataFrame(columns=["analyte_name", "cas_rn"])
    else:
        df_curated = pd.read_csv(CURATED)

    # Normalize analyte names
    df_disc["analyte_name_normalized"] = df_disc["variable_description"].apply(normalize_analyte_name)

    # Extract units
    df_disc["unit"] = df_disc["variable_description"].apply(extract_unit)

    # Infer matrix
    df_disc["matrix"] = df_disc.apply(
        lambda row: infer_matrix(row["data_file_name"], row["variable_description"]),
        axis=1,
    )

    # Get cycle ranges per variable
    cycle_summary = (
        df_disc.groupby("variable_name")
        .agg(
            analyte_name_normalized=("analyte_name_normalized", "first"),
            data_file_description=("data_file_description", "first"),
            matrix=("matrix", "first"),
            unit=("unit", "first"),
            cycle_first=("cycle", "min"),
            cycle_last=("cycle", "max"),
            cycle_count=("cycle", "nunique"),
        )
        .reset_index()
    )

    # Merge with curated CAS numbers (by normalized analyte name)
    if not df_curated.empty:
        # Create mappings from both variable_name and normalized chemical names to CAS
        cas_map = {}

        # Map by curated analyte_name (e.g., DMP, TCPy, 3-PBA)
        for _, row in df_curated.iterrows():
            cas_map[row["analyte_name"]] = row["cas_rn"]

        # Also try to match normalized chemical names (fuzzy)
        # p,p'-DDE should match "p,p'-DDE" in discovered
        for _, row in df_curated.iterrows():
            norm = _normalize_for_matching(row["analyte_name"])
            cas_map[norm] = row["cas_rn"]

        def find_cas(row):
            """Try multiple matching strategies."""
            # Try variable_name first
            if row["variable_name"] in cas_map:
                return cas_map[row["variable_name"]]
            # Try normalized analyte name
            norm = _normalize_for_matching(row["analyte_name_normalized"])
            if norm in cas_map:
                return cas_map[norm]
            # Try partial match for common abbreviations
            for key, cas in cas_map.items():
                if _normalize_for_matching(key) in norm or norm in _normalize_for_matching(key):
                    return cas
            return None

        cycle_summary["cas_rn"] = cycle_summary.apply(find_cas, axis=1)
        cycle_summary["cas_verified_source"] = cycle_summary["cas_rn"].apply(
            lambda x: "pubchem_api" if pd.notna(x) and x else ""
        )
    else:
        cycle_summary["cas_rn"] = ""
        cycle_summary["cas_verified_source"] = ""

    # Final minimal schema
    minimal_ref = cycle_summary[
        [
            "variable_name",
            "analyte_name_normalized",
            "cas_rn",
            "cas_verified_source",
            "matrix",
            "unit",
            "cycle_first",
            "cycle_last",
            "cycle_count",
            "data_file_description",
        ]
    ].rename(columns={"analyte_name_normalized": "analyte_name"})

    # Sort by variable name
    minimal_ref = minimal_ref.sort_values("variable_name")

    # Save
    out_path = Path(args.output)
    minimal_ref.to_csv(out_path, index=False)

    print(f"\n✓ Created minimal reference: {out_path}")
    print(f"  Total variables: {len(minimal_ref)}")
    print(f"  With verified CAS: {minimal_ref['cas_rn'].notna().sum()}")
    print(f"  Matrices: {minimal_ref['matrix'].value_counts().to_dict()}")
    print("\nSchema (zero AI inference):")
    print("  - analyte_name: from NHANES variable_description")
    print("  - cas_rn: from PubChem API verification only")
    print("  - matrix: inferred from data file patterns")
    print("  - unit: extracted from variable_description")
    print("  - cycle_first/last: from NHANES availability")
    print("  - NO chemical_class, NO parent_pesticide, NO specificity")


if __name__ == "__main__":
    main()

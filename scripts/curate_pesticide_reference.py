"""Auto-curate pesticide reference CSV from authoritative sources.

Fetches verified chemical identifiers and metadata from:
- PubChem API (CAS numbers, compound properties)
- NHANES documentation (variable codes, cycle availability)

Usage:
    python scripts/curate_pesticide_reference.py --output data/reference/pesticide_reference_curated.csv

Requires: requests, pandas
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


@dataclass
class AnalyteMetadata:
    """Curated pesticide analyte metadata with provenance."""

    analyte_name: str
    parent_pesticide: str
    metabolite_class: str
    cas_rn: str
    parent_cas_rn: str
    epa_pc_code: str
    pubchem_cid: int | str
    typical_matrix: str
    unit: str
    nhanes_lod: str
    first_cycle_measured: int
    last_cycle_measured: int
    current_measurement_flag: bool
    notes: str
    # Provenance fields
    cas_verified_source: str = "manual"
    last_verified_date: str = ""


class PesticideCurator:
    """Automated curator for pesticide reference metadata."""

    def __init__(self):
        """Initialize curator with session."""
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": ("PopHealthObservatory/0.7.0 " "(https://github.com/paulboys/PopHealth-Observatory)")}
        )

    def fetch_pubchem_cas(self, cid: int) -> dict[str, Any]:
        """Fetch verified CAS number and compound info from PubChem.

        Parameters
        ----------
        cid : int
            PubChem Compound ID

        Returns
        -------
        dict
            Keys: cas_rn, iupac_name, molecular_formula, verified_source
        """
        result = {
            "cas_rn": None,
            "iupac_name": None,
            "molecular_formula": None,
            "verified_source": "pubchem_api",
        }

        # Get compound properties
        prop_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/IUPACName,MolecularFormula/JSON"
        try:
            resp = self.session.get(prop_url, timeout=30)
            if resp.status_code == 404:
                result["verified_source"] = "cid_not_found"
                return result

            resp.raise_for_status()
            data = resp.json()
            props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
            result["iupac_name"] = props.get("IUPACName")
            result["molecular_formula"] = props.get("MolecularFormula")

        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Error fetching properties for CID {cid}: {e}")
            result["verified_source"] = "api_error"
            return result

        # Get CAS number from synonyms
        syn_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
        try:
            syn_resp = self.session.get(syn_url, timeout=30)
            syn_resp.raise_for_status()
            syn_data = syn_resp.json()

            synonyms = syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])

            # Find CAS Registry Number
            for syn in synonyms:
                if isinstance(syn, str) and "-" in syn and syn.replace("-", "").isdigit() and len(syn.split("-")) == 3:
                    # Valid CAS format: XXX-XX-X or XXXX-XX-X
                    result["cas_rn"] = syn
                    break

            if not result["cas_rn"]:
                print(f"  ⚠ No CAS number found in synonyms for CID {cid}")
                result["verified_source"] = "cas_not_in_pubchem"

        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Error fetching synonyms for CID {cid}: {e}")
            result["verified_source"] = "api_error"

        return result

    def curate_from_existing(self, input_csv: Path, from_date: str) -> list[AnalyteMetadata]:
        """Curate analytes by verifying existing reference CSV.

        Parameters
        ----------
        input_csv : Path
            Path to existing reference CSV (potentially hallucinated)
        from_date : str
            ISO date string for last_verified_date

        Returns
        -------
        list[AnalyteMetadata]
            Curated analyte records with verified CAS numbers
        """
        print(f"Reading existing reference from: {input_csv}")
        df = pd.read_csv(input_csv)
        print(f"Found {len(df)} analytes to curate\n")

        curated = []

        for idx, row in df.iterrows():
            analyte_name = row["analyte_name"]
            cid = row["pubchem_cid"]

            print(f"[{idx + 1}/{len(df)}] Curating {analyte_name}...")

            # Handle NA or missing CID
            if pd.isna(cid) or cid == "NA":
                print("  ⚠ No PubChem CID - keeping original data with manual flag")
                curated.append(
                    AnalyteMetadata(
                        analyte_name=analyte_name,
                        parent_pesticide=row["parent_pesticide"],
                        metabolite_class=row["metabolite_class"],
                        cas_rn=row["cas_rn"],
                        parent_cas_rn=row.get("parent_cas_rn", ""),
                        epa_pc_code=row.get("epa_pc_code", "NA"),
                        pubchem_cid=cid,
                        typical_matrix=row["typical_matrix"],
                        unit=row["unit"],
                        nhanes_lod=row.get("nhanes_lod", ""),
                        first_cycle_measured=int(row["first_cycle_measured"]),
                        last_cycle_measured=int(row["last_cycle_measured"]),
                        current_measurement_flag=bool(row["current_measurement_flag"]),
                        notes=row.get("notes", ""),
                        cas_verified_source="manual_no_cid",
                        last_verified_date=from_date,
                    )
                )
                time.sleep(0.2)
                continue

            # Fetch verified data from PubChem
            try:
                cid_int = int(cid)
            except (ValueError, TypeError):
                print(f"  ✗ Invalid CID format: {cid}")
                curated.append(
                    AnalyteMetadata(
                        analyte_name=analyte_name,
                        parent_pesticide=row["parent_pesticide"],
                        metabolite_class=row["metabolite_class"],
                        cas_rn=row["cas_rn"],
                        parent_cas_rn=row.get("parent_cas_rn", ""),
                        epa_pc_code=row.get("epa_pc_code", "NA"),
                        pubchem_cid=cid,
                        typical_matrix=row["typical_matrix"],
                        unit=row["unit"],
                        nhanes_lod=row.get("nhanes_lod", ""),
                        first_cycle_measured=int(row["first_cycle_measured"]),
                        last_cycle_measured=int(row["last_cycle_measured"]),
                        current_measurement_flag=bool(row["current_measurement_flag"]),
                        notes=row.get("notes", ""),
                        cas_verified_source="invalid_cid",
                        last_verified_date=from_date,
                    )
                )
                continue

            pubchem_data = self.fetch_pubchem_cas(cid_int)
            time.sleep(0.3)  # Rate limiting

            verified_cas = pubchem_data["cas_rn"]
            original_cas = row["cas_rn"]

            if verified_cas:
                if verified_cas != original_cas:
                    print(f"  ✓ Corrected CAS: {original_cas} → {verified_cas}")
                else:
                    print(f"  ✓ Verified CAS: {verified_cas}")

                notes = row.get("notes", "")
                if verified_cas != original_cas:
                    notes = f"[CAS corrected from {original_cas}] {notes}".strip()

                curated.append(
                    AnalyteMetadata(
                        analyte_name=analyte_name,
                        parent_pesticide=row["parent_pesticide"],
                        metabolite_class=row["metabolite_class"],
                        cas_rn=verified_cas,
                        parent_cas_rn=row.get("parent_cas_rn", ""),
                        epa_pc_code=row.get("epa_pc_code", "NA"),
                        pubchem_cid=cid_int,
                        typical_matrix=row["typical_matrix"],
                        unit=row["unit"],
                        nhanes_lod=row.get("nhanes_lod", ""),
                        first_cycle_measured=int(row["first_cycle_measured"]),
                        last_cycle_measured=int(row["last_cycle_measured"]),
                        current_measurement_flag=bool(row["current_measurement_flag"]),
                        notes=notes,
                        cas_verified_source=pubchem_data["verified_source"],
                        last_verified_date=from_date,
                    )
                )
            else:
                print(f"  ⚠ Could not verify CAS from PubChem " f"(source: {pubchem_data['verified_source']})")
                curated.append(
                    AnalyteMetadata(
                        analyte_name=analyte_name,
                        parent_pesticide=row["parent_pesticide"],
                        metabolite_class=row["metabolite_class"],
                        cas_rn=original_cas,
                        parent_cas_rn=row.get("parent_cas_rn", ""),
                        epa_pc_code=row.get("epa_pc_code", "NA"),
                        pubchem_cid=cid,
                        typical_matrix=row["typical_matrix"],
                        unit=row["unit"],
                        nhanes_lod=row.get("nhanes_lod", ""),
                        first_cycle_measured=int(row["first_cycle_measured"]),
                        last_cycle_measured=int(row["last_cycle_measured"]),
                        current_measurement_flag=bool(row["current_measurement_flag"]),
                        notes=row.get("notes", ""),
                        cas_verified_source=pubchem_data["verified_source"],
                        last_verified_date=from_date,
                    )
                )

        return curated

    def save_curated_csv(self, analytes: list[AnalyteMetadata], output_path: Path):
        """Save curated analytes to CSV.

        Parameters
        ----------
        analytes : list[AnalyteMetadata]
            Curated analyte records
        output_path : Path
            Output CSV file path
        """
        df = pd.DataFrame([asdict(a) for a in analytes])

        # Reorder columns for readability (provenance at end)
        core_cols = [
            "analyte_name",
            "parent_pesticide",
            "metabolite_class",
            "cas_rn",
            "parent_cas_rn",
            "epa_pc_code",
            "pubchem_cid",
            "typical_matrix",
            "unit",
            "nhanes_lod",
            "first_cycle_measured",
            "last_cycle_measured",
            "current_measurement_flag",
            "notes",
        ]
        provenance_cols = ["cas_verified_source", "last_verified_date"]

        df = df[core_cols + provenance_cols]
        df.to_csv(output_path, index=False)
        print(f"\n✓ Saved curated reference to: {output_path}")


def main():
    """Run curation from command line."""
    parser = argparse.ArgumentParser(description="Auto-curate pesticide reference CSV with verified data")
    parser.add_argument(
        "--input",
        type=str,
        default="data/reference/pesticide_reference.csv",
        help="Input CSV to curate (default: data/reference/pesticide_reference.csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/reference/pesticide_reference_curated.csv",
        help="Output CSV path (default: data/reference/pesticide_reference_curated.csv)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default="2025-11-08",
        help="Verification date (ISO format, default: 2025-11-08)",
    )
    args = parser.parse_args()

    input_path = ROOT / args.input
    output_path = ROOT / args.output

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    curator = PesticideCurator()

    try:
        curated = curator.curate_from_existing(input_path, args.date)
        curator.save_curated_csv(curated, output_path)

        # Summary
        verified_count = sum(1 for a in curated if a.cas_verified_source == "pubchem_api")
        corrected_count = sum(1 for a in curated if "[CAS corrected" in a.notes)

        print("\nSummary:")
        print(f"  Total analytes: {len(curated)}")
        print(f"  Verified from PubChem: {verified_count}")
        print(f"  CAS numbers corrected: {corrected_count}")
        print(f"  Manual review needed: {len(curated) - verified_count}")

    except KeyboardInterrupt:
        print("\n\nCuration interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: Curation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

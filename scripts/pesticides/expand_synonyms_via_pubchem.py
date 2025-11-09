"""PubChem synonym expansion for pesticide analytes.

This script queries the PubChem REST API to retrieve all registered synonyms
for pesticide chemicals identified by CAS Registry Number. The output synonym
map replaces fuzzy string matching with authoritative chemical nomenclature.

Strategy:
1. Load minimal analyte reference containing CAS RNs.
2. For each unique CAS RN, query PubChem synonyms endpoint.
3. Store all synonyms (common names, abbreviations, IUPAC, trade names).
4. Generate structured synonym map CSV for downstream classification matching.

Coverage:
- PubChem success: 57/59 CAS RNs (96.6%)
- Total synonyms: 5,451 entries
- Known gaps:
  * CAS 70458-82-3 (3-PBA): Not in PubChem (may be invalid/outdated CAS)
  * CAS 814-24-8 (DMP): Not in PubChem (may be invalid/outdated CAS)

Manual curation needed for gap cases using NHANES codebooks or CDC Fourth Report.

Usage:
    python scripts/pesticides/expand_synonyms_via_pubchem.py

Output:
    data/reference/config/pubchem_synonyms.csv

API Rate Limiting:
    - 0.3 second delay between requests (conservative; PubChem allows ~5 req/sec)
    - Timeout: 10 seconds per request
    - Retries: 2 attempts with exponential backoff

PROVENANCE:
    Data source: PubChem REST API (NCBI/NIH)
    Endpoint: https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/<CAS>/synonyms/JSON
    Last updated: Dynamically via API (always current)
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import requests


def fetch_pubchem_synonyms(cas_rn: str, retries: int = 2) -> list[str]:
    """Fetch all PubChem synonyms for a CAS Registry Number.

    Parameters
    ----------
    cas_rn : str
        CAS Registry Number (e.g., "50-29-3" for DDT)
    retries : int
        Number of retry attempts on network failure

    Returns
    -------
    list[str]
        List of all registered synonyms, or empty list on failure

    Notes
    -----
    Known limitations:
    - CAS 70458-82-3 (3-PBA): Not found in PubChem (may be invalid/outdated CAS)
    - CAS 814-24-8 (DMP): Not found in PubChem (may be invalid/outdated CAS)
    These cases require manual curation from NHANES codebooks or CDC Fourth Report.
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas_rn}/synonyms/JSON"

    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Extract synonym list from nested structure
            info_list = data.get("InformationList", {}).get("Information", [])
            if info_list:
                synonyms = info_list[0].get("Synonym", [])
                return synonyms
            return []

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # CAS not found in PubChem
                print(f"  ⚠ CAS {cas_rn} not found in PubChem (404)")
                return []
            elif attempt < retries:
                wait = 2**attempt  # Exponential backoff: 1s, 2s
                print(f"  ⚠ HTTP error for {cas_rn}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ✗ Failed to fetch {cas_rn} after {retries} retries: {e}")
                return []

        except requests.exceptions.RequestException as e:
            if attempt < retries:
                wait = 2**attempt
                print(f"  ⚠ Network error for {cas_rn}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ✗ Network error for {cas_rn}: {e}")
                return []

        except (KeyError, ValueError) as e:
            print(f"  ✗ JSON parse error for {cas_rn}: {e}")
            return []

    return []


def load_minimal_reference(path: Path) -> list[dict]:
    """Load minimal analyte reference CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Minimal reference not found: {path}")

    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def expand_reference_synonyms(input_csv: Path, output_csv: Path) -> None:
    """Expand minimal reference with PubChem synonym mappings.

    Parameters
    ----------
    input_csv : Path
        Path to minimal pesticide reference CSV (must have cas_rn, analyte_name columns)
    output_csv : Path
        Path to output synonym map CSV
    """
    print(f"Loading minimal reference from: {input_csv}")
    rows = load_minimal_reference(input_csv)

    # Extract unique CAS RNs (skip empty or placeholder values)
    cas_to_analyte = {}
    for row in rows:
        cas = row.get("cas_rn", "").strip()
        analyte = row.get("analyte_name", "").strip()
        if cas and cas.lower() not in {"unknown", "na", "n/a", ""}:
            cas_to_analyte[cas] = analyte

    print(f"Found {len(cas_to_analyte)} unique CAS RNs to query")

    # Fetch synonyms with rate limiting
    synonym_map: dict[str, list[str]] = {}
    for i, (cas, analyte) in enumerate(cas_to_analyte.items(), start=1):
        print(f"[{i}/{len(cas_to_analyte)}] Fetching synonyms for {cas} ({analyte})...")
        synonyms = fetch_pubchem_synonyms(cas)

        if synonyms:
            synonym_map[cas] = synonyms
            print(f"  ✓ Retrieved {len(synonyms)} synonyms")
        else:
            synonym_map[cas] = []
            print("  ✗ No synonyms found")

        # Rate limiting: 0.3s between requests (~3.3 req/sec; PubChem allows 5/sec)
        if i < len(cas_to_analyte):
            time.sleep(0.3)

    # Write synonym map to CSV
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["cas_rn", "analyte_name", "synonym", "synonym_normalized"])

        for cas, synonyms in synonym_map.items():
            analyte = cas_to_analyte[cas]
            for syn in synonyms:
                # Also store normalized form for case-insensitive matching
                syn_norm = syn.lower().strip()
                writer.writerow([cas, analyte, syn, syn_norm])

    print(f"\n✓ Synonym map written to: {output_csv}")
    print(f"  Total CAS entries: {len(synonym_map)}")
    print(f"  Total synonym rows: {sum(len(syns) for syns in synonym_map.values())}")

    # Summary stats
    with_synonyms = sum(1 for syns in synonym_map.values() if syns)
    without_synonyms = len(synonym_map) - with_synonyms
    print(f"  CAS with synonyms: {with_synonyms}")
    print(f"  CAS without synonyms: {without_synonyms}")


def main() -> None:
    """Run PubChem synonym expansion."""
    root = Path(__file__).parent.parent.parent
    input_path = root / "data" / "reference" / "minimal" / "pesticide_reference_minimal.csv"
    output_path = root / "data" / "reference" / "config" / "pubchem_synonyms.csv"

    print("=" * 80)
    print("PubChem Synonym Expansion for Pesticide Analytes")
    print("=" * 80)

    expand_reference_synonyms(input_path, output_path)

    print("\n" + "=" * 80)
    print("Next steps:")
    print("  1. Review generated synonym map for accuracy")
    print("  2. Use synonym map in enrich_classification_round.py for exact matching")
    print("  3. Commit synonym CSV to git (small file, authoritative source)")
    print("=" * 80)


if __name__ == "__main__":
    main()

"""Classification expansion evidence logging for pesticide analytes.

This script identifies unclassified analytes and attempts exact synonym-based
matching against CDC Fourth Report classification data using PubChem synonyms.
Results are logged to data/reference/evidence/ for reproducible manual review.

Strategy:
1. Load minimal analyte reference and PubChem synonym map.
2. Identify analytes missing chemical_class (unclassified).
3. Match analyte names against CDC classification list via exact synonym lookup.
4. Fallback to fuzzy matching (normalized string similarity) if no synonym match.
5. Log unresolved analytes with candidate matches to evidence CSV.

Usage:
    python scripts/pesticides/enrich_classification_round.py

Prerequisites:
    - Run expand_synonyms_via_pubchem.py first to generate synonym map

Output:
    data/reference/evidence/unclassified_YYYY-MM-DD.csv

"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

# ============================================================================
# CDC Fourth Report Classification Reference Data
# ============================================================================
# PROVENANCE:
#   - chemical_class: Extracted from CDC Fourth National Report on Human Exposure
#     to Environmental Chemicals (2021+), Table 1 and supplemental data tables.
#     Source: https://www.cdc.gov/exposurereport/
#
#   - chemical_subclass: PROVISIONAL (currently stripped; requires verification)
#     Previously contained structural chemistry inferences (e.g., "Chlorinated benzene",
#     "DDT-related", "Cyclodiene") but these are NOT direct CDC Fourth Report labels.
#     Subclass refinement requires cross-reference with:
#       * PubChem chemical taxonomy
#       * ATSDR Toxicological Profiles
#       * Peer-reviewed pesticide classification literature
#
# VERIFICATION CHECKLIST:
#   See inline comments below each entry for PubChem verification links.
#   Subclass values should remain empty ("") until authoritative source confirmed.
#
# Format: (normalized_cdc_name, chemical_class, chemical_subclass)
# ============================================================================

CDC_CLASSIFICATIONS = [
    # Organochlorine Pesticides
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/hexachlorobenzene
    ("hexachlorobenzene", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/mirex
    ("mirex", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/ddt
    ("ddt", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/dde
    ("dde", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/oxychlordane
    ("oxychlordane", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/trans-nonachlor
    ("trans-nonachlor", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/aldrin
    ("aldrin", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/dieldrin
    ("dieldrin", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/endrin
    ("endrin", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/heptachlor
    ("heptachlor", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/beta-hexachlorocyclohexane
    ("beta-hexachlorocyclohexane", "Organochlorine", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/gamma-hexachlorocyclohexane
    ("gamma-hexachlorocyclohexane", "Organochlorine", ""),
    # Pyrethroid Metabolites
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/3-phenoxybenzoic-acid
    ("3-phenoxybenzoic acid", "Pyrethroid metabolite", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/3-phenoxybenzoic-acid
    ("3-pba", "Pyrethroid metabolite", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/4-fluoro-3-phenoxybenzoic-acid
    ("4-fluoro-3-phenoxybenzoic acid", "Pyrethroid metabolite", ""),
    # Organophosphate Metabolites (Dialkyl Phosphates - DAPs)
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/dimethyl-phosphate
    ("dimethylphosphate", "Organophosphate metabolite", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/diethyl-phosphate
    ("diethylphosphate", "Organophosphate metabolite", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/dimethylthiophosphate
    ("dimethylthiophosphate", "Organophosphate metabolite", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/diethylthiophosphate
    ("diethylthiophosphate", "Organophosphate metabolite", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/dimethyldithiophosphate
    ("dimethyldithiophosphate", "Organophosphate metabolite", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/diethyldithiophosphate
    ("diethyldithiophosphate", "Organophosphate metabolite", ""),
    # Current-Use Organophosphate Pesticides
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/malathion
    ("malathion", "Organophosphate", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/chlorpyrifos
    ("chlorpyrifos", "Organophosphate", ""),
    # Phenoxy Herbicides
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/2,4-dichlorophenoxyacetic-acid
    ("2,4-d", "Phenoxy herbicide", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/2,4,5-trichlorophenoxyacetic-acid
    ("2,4,5-t", "Phenoxy herbicide", ""),
    # Triazine Herbicides
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/atrazine
    ("atrazine", "Triazine herbicide", ""),
    # Organophosphonate Herbicides
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/glyphosate
    ("glyphosate", "Organophosphonate herbicide", ""),
    # Chlorophenols (Environmental Contaminants)
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/2,5-dichlorophenol
    ("2,5-dichlorophenol", "Chlorophenol", ""),
    # Verify: https://pubchem.ncbi.nlm.nih.gov/compound/2,4-dichlorophenol
    ("2,4-dichlorophenol", "Chlorophenol", ""),
]


def load_pubchem_synonym_map(path: Path) -> dict[str, set[str]]:
    """Load PubChem synonym map indexed by normalized synonym.

    Parameters
    ----------
    path : Path
        Path to pubchem_synonyms.csv (columns: cas_rn, analyte_name, synonym, synonym_normalized)

    Returns
    -------
    dict[str, set[str]]
        Mapping from normalized synonym → set of original analyte names
    """
    if not path.exists():
        return {}

    synonym_index: dict[str, set[str]] = {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            synonym_norm = row.get("synonym_normalized", "").strip()
            analyte = row.get("analyte_name", "").strip()
            if synonym_norm and analyte:
                if synonym_norm not in synonym_index:
                    synonym_index[synonym_norm] = set()
                synonym_index[synonym_norm].add(analyte)

    return synonym_index


def _normalize_name(name: str) -> str:
    """Normalize analyte name for matching: lowercase, remove punctuation, collapse spaces."""
    if not name:
        return ""
    # Lowercase
    norm = name.lower()
    # Remove common punctuation (keep hyphens for chemical names like "2,4-D")
    norm = re.sub(r"[^\w\s,-]", "", norm)
    # Collapse multiple spaces
    norm = re.sub(r"\s+", " ", norm)
    return norm.strip()


def _compute_similarity_score(query: str, candidate: str) -> float:
    """Simple normalized substring similarity score.

    Returns score between 0 (no match) and 1 (exact match).
    Uses length-normalized longest common substring approach.
    """
    query_norm = _normalize_name(query)
    cand_norm = _normalize_name(candidate)

    if not query_norm or not cand_norm:
        return 0.0

    # Exact match
    if query_norm == cand_norm:
        return 1.0

    # Substring match (query in candidate or vice versa)
    if query_norm in cand_norm or cand_norm in query_norm:
        # Score based on length ratio
        shorter = min(len(query_norm), len(cand_norm))
        longer = max(len(query_norm), len(cand_norm))
        return shorter / longer

    # Token overlap (simple word-level Jaccard)
    query_tokens = set(query_norm.split())
    cand_tokens = set(cand_norm.split())
    if not query_tokens or not cand_tokens:
        return 0.0

    intersection = query_tokens & cand_tokens
    union = query_tokens | cand_tokens
    return len(intersection) / len(union) if union else 0.0


def find_classification_candidates(
    analyte_name: str,
    cdc_list: list[tuple[str, str, str]],
    synonym_map: dict[str, set[str]],
    threshold: float = 0.3,
) -> list[tuple[str, str, str, float, str]]:
    """Find CDC classification candidates for an analyte using synonym matching + fallback fuzzy.

    Parameters
    ----------
    analyte_name : str
        Analyte name to classify
    cdc_list : list[tuple[str, str, str]]
        CDC classification tuples (cdc_name, chemical_class, chemical_subclass)
    synonym_map : dict[str, set[str]]
        PubChem synonym index (normalized synonym → set of analyte names)
    threshold : float
        Minimum similarity score for fuzzy fallback (0-1)

    Returns
    -------
    list[tuple[str, str, str, float, str]]
        List of (cdc_name, chemical_class, chemical_subclass, score, match_method)
        sorted by score descending
    """
    candidates = []
    analyte_norm = _normalize_name(analyte_name)

    # Strategy 1: Exact synonym match via PubChem (score = 1.0)
    if analyte_norm in synonym_map:
        matched_analytes = synonym_map[analyte_norm]
        for cdc_name, chem_class, chem_subclass in cdc_list:
            cdc_norm = _normalize_name(cdc_name)
            if cdc_norm in synonym_map and synonym_map[cdc_norm] & matched_analytes:
                # Both analyte and CDC name share common PubChem synonyms
                candidates.append((cdc_name, chem_class, chem_subclass, 1.0, "pubchem_synonym"))

    # Strategy 2: Direct CDC name in synonym map (score = 1.0)
    for cdc_name, chem_class, chem_subclass in cdc_list:
        cdc_norm = _normalize_name(cdc_name)
        if cdc_norm == analyte_norm:
            candidates.append((cdc_name, chem_class, chem_subclass, 1.0, "exact_match"))
        elif cdc_norm in synonym_map and analyte_name in synonym_map[cdc_norm]:
            candidates.append((cdc_name, chem_class, chem_subclass, 1.0, "pubchem_synonym"))

    # Strategy 3: Fuzzy fallback (only if no synonym matches found)
    if not candidates:
        for cdc_name, chem_class, chem_subclass in cdc_list:
            score = _compute_similarity_score(analyte_name, cdc_name)
            if score >= threshold:
                candidates.append((cdc_name, chem_class, chem_subclass, score, "fuzzy"))

    # Sort by score descending, then by match method (pubchem > exact > fuzzy)
    method_priority = {"pubchem_synonym": 0, "exact_match": 1, "fuzzy": 2}
    candidates.sort(key=lambda x: (-x[3], method_priority.get(x[4], 99)))
    return candidates


def load_minimal_reference(path: Path) -> list[dict]:
    """Load minimal analyte reference CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Minimal reference not found: {path}")

    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def identify_unclassified(analytes: list[dict]) -> list[dict]:
    """Identify analytes missing chemical_class field."""
    unclassified = []
    for a in analytes:
        # Check if chemical_class field is missing or empty
        if not a.get("chemical_class", "").strip():
            unclassified.append(a)
    return unclassified


def log_evidence(
    unclassified: list[dict],
    output_path: Path,
    cdc_list: list[tuple[str, str, str]],
    synonym_map: dict[str, set[str]],
) -> None:
    """Log unclassified analytes with candidate matches to evidence CSV.

    Parameters
    ----------
    unclassified : list[dict]
        Unclassified analyte records
    output_path : Path
        Output evidence CSV path
    cdc_list : list[tuple[str, str, str]]
        CDC classification reference
    synonym_map : dict[str, set[str]]
        PubChem synonym index
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        fieldnames = [
            "variable_name",
            "analyte_name",
            "normalized_name",
            "candidate_cdc_name",
            "candidate_class",
            "candidate_subclass",
            "similarity_score",
            "match_method",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        for analyte in unclassified:
            var_name = analyte.get("variable_name", "")
            analyte_name = analyte.get("analyte_name", "")
            norm_name = _normalize_name(analyte_name)

            candidates = find_classification_candidates(analyte_name, cdc_list, synonym_map, threshold=0.25)

            if candidates:
                # Write best candidate (highest score)
                cdc_name, chem_class, chem_subclass, score, method = candidates[0]
                writer.writerow(
                    {
                        "variable_name": var_name,
                        "analyte_name": analyte_name,
                        "normalized_name": norm_name,
                        "candidate_cdc_name": cdc_name,
                        "candidate_class": chem_class,
                        "candidate_subclass": chem_subclass,
                        "similarity_score": f"{score:.3f}",
                        "match_method": method,
                    }
                )
            else:
                # No candidates; log with empty candidate fields
                writer.writerow(
                    {
                        "variable_name": var_name,
                        "analyte_name": analyte_name,
                        "normalized_name": norm_name,
                        "candidate_cdc_name": "",
                        "candidate_class": "",
                        "candidate_subclass": "",
                        "similarity_score": "0.000",
                        "match_method": "none",
                    }
                )


def main() -> None:
    """Run classification expansion evidence logging."""
    # Paths
    root = Path(__file__).parent.parent.parent
    minimal_ref_path = root / "data" / "reference" / "minimal" / "pesticide_reference_minimal.csv"
    synonym_map_path = root / "data" / "reference" / "config" / "pubchem_synonyms.csv"
    evidence_dir = root / "data" / "reference" / "evidence"
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = evidence_dir / f"unclassified_{today}.csv"

    print(f"Loading minimal reference from: {minimal_ref_path}")
    analytes = load_minimal_reference(minimal_ref_path)
    print(f"Total analytes: {len(analytes)}")

    print(f"Loading PubChem synonym map from: {synonym_map_path}")
    synonym_map = load_pubchem_synonym_map(synonym_map_path)
    if synonym_map:
        print(f"Loaded {len(synonym_map)} normalized synonyms")
    else:
        print("⚠ Warning: No synonym map found; falling back to fuzzy matching only")
        print("  Run expand_synonyms_via_pubchem.py first for best results")

    print("Identifying unclassified analytes...")
    unclassified = identify_unclassified(analytes)
    print(f"Unclassified analytes: {len(unclassified)}")

    if not unclassified:
        print("No unclassified analytes found. All analytes have chemical_class assigned.")
        return

    print(f"Logging evidence to: {output_path}")
    log_evidence(unclassified, output_path, CDC_CLASSIFICATIONS, synonym_map)
    print(f"Evidence logged successfully. Review {output_path} for candidate matches.")

    # Summary stats
    with output_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        with_candidates = sum(1 for r in rows if r["candidate_cdc_name"])
        no_candidates = len(rows) - with_candidates
        pubchem_matches = sum(1 for r in rows if r.get("match_method") == "pubchem_synonym")
        exact_matches = sum(1 for r in rows if r.get("match_method") == "exact_match")
        fuzzy_matches = sum(1 for r in rows if r.get("match_method") == "fuzzy")

    print("\nSummary:")
    print(f"  - Total unclassified: {len(rows)}")
    print(f"  - With candidate matches: {with_candidates}")
    print(f"    • PubChem synonym matches: {pubchem_matches}")
    print(f"    • Exact name matches: {exact_matches}")
    print(f"    • Fuzzy fallback matches: {fuzzy_matches}")
    print(f"  - No candidate matches: {no_candidates}")


if __name__ == "__main__":
    main()

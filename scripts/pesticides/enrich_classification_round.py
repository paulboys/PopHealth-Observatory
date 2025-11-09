"""Classification expansion evidence logging for pesticide analytes.

This script identifies unclassified analytes and attempts normalization-based
matching against CDC Fourth Report classification data. Results are logged
to data/reference/evidence/ for reproducible manual review and enrichment.

Strategy:
1. Load minimal analyte reference.
2. Identify analytes missing chemical_class (unclassified).
3. Normalize analyte names (lowercase, strip punctuation, collapse whitespace).
4. Attempt substring/token matching against CDC classification list.
5. Score matches by normalized string similarity.
6. Log unresolved analytes with candidate matches to evidence CSV.

Usage:
    python scripts/pesticides/enrich_classification_round.py

Output:
    data/reference/evidence/unclassified_YYYY-MM-DD.csv

"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

# CDC Fourth Report classification data (subset; expand as needed)
# Format: (normalized_cdc_name, chemical_class, chemical_subclass)
CDC_CLASSIFICATIONS = [
    ("hexachlorobenzene", "Organochlorine", "Chlorinated benzene"),
    ("mirex", "Organochlorine", "Chlordane-related"),
    ("ddt", "Organochlorine", "DDT-related"),
    ("dde", "Organochlorine", "DDT metabolite"),
    ("oxychlordane", "Organochlorine", "Chlordane-related"),
    ("trans-nonachlor", "Organochlorine", "Chlordane-related"),
    ("aldrin", "Organochlorine", "Cyclodiene"),
    ("dieldrin", "Organochlorine", "Cyclodiene"),
    ("endrin", "Organochlorine", "Cyclodiene"),
    ("heptachlor", "Organochlorine", "Cyclodiene"),
    ("beta-hexachlorocyclohexane", "Organochlorine", "HCH"),
    ("gamma-hexachlorocyclohexane", "Organochlorine", "HCH (Lindane)"),
    ("3-phenoxybenzoic acid", "Pyrethroid metabolite", "Common metabolite"),
    ("3-pba", "Pyrethroid metabolite", "Common metabolite"),
    ("4-fluoro-3-phenoxybenzoic acid", "Pyrethroid metabolite", "Cyfluthrin-specific"),
    ("dimethylphosphate", "Organophosphate metabolite", "DAP"),
    ("diethylphosphate", "Organophosphate metabolite", "DAP"),
    ("dimethylthiophosphate", "Organophosphate metabolite", "DAP"),
    ("diethylthiophosphate", "Organophosphate metabolite", "DAP"),
    ("dimethyldithiophosphate", "Organophosphate metabolite", "DAP"),
    ("diethyldithiophosphate", "Organophosphate metabolite", "DAP"),
    ("malathion", "Organophosphate", "Current-use OP"),
    ("chlorpyrifos", "Organophosphate", "Current-use OP"),
    ("2,4-d", "Phenoxy herbicide", "Chlorophenoxy"),
    ("2,4,5-t", "Phenoxy herbicide", "Chlorophenoxy"),
    ("atrazine", "Triazine herbicide", "Current-use herbicide"),
    ("glyphosate", "Organophosphonate herbicide", "Current-use herbicide"),
    ("2,5-dichlorophenol", "Chlorophenol", "Environmental contaminant"),
    ("2,4-dichlorophenol", "Chlorophenol", "Environmental contaminant"),
]


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
    analyte_name: str, cdc_list: list[tuple[str, str, str]], threshold: float = 0.3
) -> list[tuple[str, str, str, float]]:
    """Find CDC classification candidates for an analyte above similarity threshold.

    Parameters
    ----------
    analyte_name : str
        Analyte name to classify
    cdc_list : list[tuple[str, str, str]]
        CDC classification tuples (cdc_name, chemical_class, chemical_subclass)
    threshold : float
        Minimum similarity score (0-1)

    Returns
    -------
    list[tuple[str, str, str, float]]
        List of (cdc_name, chemical_class, chemical_subclass, score) sorted by score descending
    """
    candidates = []
    for cdc_name, chem_class, chem_subclass in cdc_list:
        score = _compute_similarity_score(analyte_name, cdc_name)
        if score >= threshold:
            candidates.append((cdc_name, chem_class, chem_subclass, score))

    # Sort by score descending
    candidates.sort(key=lambda x: x[3], reverse=True)
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


def log_evidence(unclassified: list[dict], output_path: Path, cdc_list: list[tuple[str, str, str]]) -> None:
    """Log unclassified analytes with candidate matches to evidence CSV.

    Parameters
    ----------
    unclassified : list[dict]
        Unclassified analyte records
    output_path : Path
        Output evidence CSV path
    cdc_list : list[tuple[str, str, str]]
        CDC classification reference
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
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        for analyte in unclassified:
            var_name = analyte.get("variable_name", "")
            analyte_name = analyte.get("analyte_name", "")
            norm_name = _normalize_name(analyte_name)

            candidates = find_classification_candidates(analyte_name, cdc_list, threshold=0.25)

            if candidates:
                # Write best candidate (highest score)
                cdc_name, chem_class, chem_subclass, score = candidates[0]
                writer.writerow(
                    {
                        "variable_name": var_name,
                        "analyte_name": analyte_name,
                        "normalized_name": norm_name,
                        "candidate_cdc_name": cdc_name,
                        "candidate_class": chem_class,
                        "candidate_subclass": chem_subclass,
                        "similarity_score": f"{score:.3f}",
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
                    }
                )


def main() -> None:
    """Run classification expansion evidence logging."""
    # Paths
    root = Path(__file__).parent.parent.parent
    minimal_ref_path = root / "data" / "reference" / "minimal" / "pesticide_reference_minimal.csv"
    evidence_dir = root / "data" / "reference" / "evidence"
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = evidence_dir / f"unclassified_{today}.csv"

    print(f"Loading minimal reference from: {minimal_ref_path}")
    analytes = load_minimal_reference(minimal_ref_path)
    print(f"Total analytes: {len(analytes)}")

    print("Identifying unclassified analytes...")
    unclassified = identify_unclassified(analytes)
    print(f"Unclassified analytes: {len(unclassified)}")

    if not unclassified:
        print("No unclassified analytes found. All analytes have chemical_class assigned.")
        return

    print(f"Logging evidence to: {output_path}")
    log_evidence(unclassified, output_path, CDC_CLASSIFICATIONS)
    print(f"Evidence logged successfully. Review {output_path} for candidate matches.")

    # Summary stats
    with output_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        with_candidates = sum(1 for r in rows if r["candidate_cdc_name"])
        no_candidates = len(rows) - with_candidates

    print("\nSummary:")
    print(f"  - Total unclassified: {len(rows)}")
    print(f"  - With candidate matches: {with_candidates}")
    print(f"  - No candidate matches: {no_candidates}")


if __name__ == "__main__":
    main()

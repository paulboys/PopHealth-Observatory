"""Pesticide context integration scaffolding.

This module provides early-stage utilities for linking NHANES pesticide / metabolite
laboratory analytes to external narrative and structured sources. It will evolve into
an ingestion + retrieval layer supporting RAG pipelines.

Current capabilities (MVP):
  - Load curated analyte reference CSV (data/reference/pesticide_reference.csv)
  - Load source registry YAML (pesticide_sources.yml)
  - Simple lookup by analyte name or CAS RN
  - Basic fuzzy suggestions when no direct match

Planned (future iterations):
  - Automated source fetching & text extraction
  - Chemical entity recognition & snippet generation
  - Embedding index construction and semantic retrieval
  - RAG-style context assembly for Q&A

"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


DATA_REFERENCE_DIR = Path("data/reference")
# Updated directory layout after cleanup:
#  minimal/      -> minimal reference
#  classified/   -> enriched classified reference
#  legacy/       -> quarantined / historical artifacts
#  config/       -> source registries & YAML config
#  discovery/    -> raw NHANES variable discovery artifacts
#  evidence/     -> mapping attempt evidence
REFERENCE_CSV = DATA_REFERENCE_DIR / "minimal" / "pesticide_reference_minimal.csv"
REFERENCE_CSV_CLASSIFIED = DATA_REFERENCE_DIR / "classified" / "pesticide_reference_classified.csv"
REFERENCE_CSV_LEGACY_AI = DATA_REFERENCE_DIR / "legacy" / "pesticide_reference_legacy_ai.csv"
REFERENCE_CSV_VERIFIED = DATA_REFERENCE_DIR / "legacy" / "pesticide_reference_verified.csv"
SOURCES_YAML = DATA_REFERENCE_DIR / "config" / "pesticide_sources.yml"


@dataclass
class PesticideAnalyte:
    """Minimal pesticide analyte reference with optional CDC classifications.

    Core fields sourced from:
    - NHANES variable metadata (direct observation)
    - PubChem API verification (cas_rn only)

    Optional classification fields sourced from:
    - CDC Fourth National Report (chemical_class, chemical_subclass)

    NO parent_pesticide, NO specificity inference.
    """

    variable_name: str
    analyte_name: str
    cas_rn: str
    cas_verified_source: str
    matrix: str  # urine, serum, unknown
    unit: str
    cycle_first: int
    cycle_last: int
    cycle_count: int
    data_file_description: str
    # Optional CDC classification fields
    chemical_class: str = ""
    chemical_subclass: str = ""
    classification_source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "analyte_name": self.analyte_name,
            "cas_rn": self.cas_rn,
            "cas_verified_source": self.cas_verified_source,
            "matrix": self.matrix,
            "unit": self.unit,
            "cycle_first": self.cycle_first,
            "cycle_last": self.cycle_last,
            "cycle_count": self.cycle_count,
            "data_file_description": self.data_file_description,
            "chemical_class": self.chemical_class,
            "chemical_subclass": self.chemical_subclass,
            "classification_source": self.classification_source,
            # Backward compatibility fields expected by legacy tests
            "metabolite_class": "",
            "parent_pesticide": "",
            "current_measurement_flag": True,
        }


def _normalize(s: str) -> str:
    """Normalize strings for loose matching.

    Previous implementation only removed hyphens/underscores which failed a test
    expecting partial matches for names containing commas/apostrophes (e.g., "p,p'-DDE").
    We now collapse to lowercase alphanumerics to make substring suggestion logic
    more robust for metabolite names.
    """
    import re  # local import to avoid global cost

    return re.sub(r"[^a-z0-9]", "", s.lower())


def load_analyte_reference(path: Path = REFERENCE_CSV, allow_legacy_ai: bool = False) -> list[PesticideAnalyte]:
    """Load pesticide analyte reference CSV (minimal or classified).

    Parameters
    ----------
    path : Path, default=REFERENCE_CSV
        Path to the reference CSV file. Auto-detects classified vs minimal schema.
    allow_legacy_ai : bool, default=False
        If True, permits loading the legacy AI-generated file without warning.
        If False and legacy file is detected, raises ValueError.

    Returns
    -------
    list[PesticideAnalyte]
        Parsed analyte records.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If legacy AI file is being loaded without explicit permission.
    """
    # Prefer classified file if caller passed default minimal path and classified exists
    if path == REFERENCE_CSV and REFERENCE_CSV_CLASSIFIED.exists():
        path = REFERENCE_CSV_CLASSIFIED
        print(f"INFO: Using classified reference file: {path}")
    # Otherwise prefer verified file if explicit path missing
    elif not path.exists() and REFERENCE_CSV_VERIFIED.exists():
        path = REFERENCE_CSV_VERIFIED
        print(f"INFO: Using verified reference file: {path}")

    # Fallback compatibility: if new structured path not found, try old flat locations
    if not path.exists():
        legacy_flat_candidates = [
            DATA_REFERENCE_DIR / "pesticide_reference_minimal.csv",
            DATA_REFERENCE_DIR / "pesticide_reference_classified.csv",
        ]
        for candidate in legacy_flat_candidates:
            if candidate.exists():
                print(f"INFO: Fallback to legacy flat reference path: {candidate}")
                path = candidate
                break

    # Check for legacy AI file
    if path.name == "pesticide_reference_legacy_ai.csv" and not allow_legacy_ai:
        raise ValueError(
            f"Attempted to load AI-generated legacy file: {path}\n"
            "This file contains unverified parent_pesticide mappings.\n"
            "To use this file for historical reproduction only, set allow_legacy_ai=True.\n"
            f"Preferred: Use {REFERENCE_CSV} (minimal schema with zero inference)."
        )

    if not path.exists():  # pragma: no cover
        raise FileNotFoundError(f"Reference CSV not found: {path}")

    records: list[PesticideAnalyte] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            records.append(
                PesticideAnalyte(
                    variable_name=row.get("variable_name", ""),
                    analyte_name=row.get("analyte_name", ""),
                    cas_rn=row.get("cas_rn", ""),
                    cas_verified_source=row.get("cas_verified_source", ""),
                    matrix=row.get("matrix", "unknown"),
                    unit=row.get("unit", ""),
                    cycle_first=int(row.get("cycle_first", 0)),
                    cycle_last=int(row.get("cycle_last", 0)),
                    cycle_count=int(row.get("cycle_count", 0)),
                    data_file_description=row.get("data_file_description", ""),
                    # Optional classification fields (only in classified reference)
                    chemical_class=row.get("chemical_class", ""),
                    chemical_subclass=row.get("chemical_subclass", ""),
                    classification_source=row.get("classification_source", ""),
                )
            )
    return records


def get_pesticide_info(query: str) -> dict[str, Any]:  # pragma: no cover - thin wrapper
    """Backward compatible query helper returning match + suggestions structure.

    This preserves the shape legacy tests expect while using the new minimal
    schema internally. Matching is performed against analyte_name (case-insensitive)
    and CAS number. Suggestions are simple substring matches when exact count !=1.
    """
    records = load_analyte_reference()
    norm_query = _normalize(query)
    exact: list[PesticideAnalyte] = []
    for r in records:
        if _normalize(r.analyte_name) == norm_query or (r.cas_rn and r.cas_rn == query):
            exact.append(r)
    if len(exact) == 1:
        return {"count": 1, "match": exact[0].to_dict(), "suggestions": []}
    # suggestions
    suggestions: list[str] = []
    for r in records:
        if norm_query and norm_query in _normalize(r.analyte_name):
            suggestions.append(r.analyte_name)
    return {"count": len(exact), "match": exact[0].to_dict() if exact else None, "suggestions": suggestions[:10]}


def load_source_registry(path: Path = SOURCES_YAML) -> list[dict[str, Any]]:
    """Load narrative source registry YAML describing external sources.

    Parameters
    ----------
    path : Path, default=SOURCES_YAML
        Path to the YAML registry.

    Returns
    -------
    list[dict[str, Any]]
        List of source descriptor dictionaries (may be empty if structure unexpected).

    Raises
    ------
    FileNotFoundError
        If the YAML file is missing.
    RuntimeError
        If PyYAML is not installed.
    """
    if not path.exists():  # pragma: no cover
        raise FileNotFoundError(f"Sources YAML not found: {path}")
    if yaml is None:  # pragma: no cover
        raise RuntimeError("pyyaml not installed; add to extras to use source registry")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, list) else []


def find_analyte(query: str, analytes: list[PesticideAnalyte]) -> PesticideAnalyte | None:
    """Attempt exact analyte, CAS RN, or variable name match (normalized).

    Parameters
    ----------
    query : str
        User input analyte string, CAS RN, or variable name.
    analytes : list[PesticideAnalyte]
        Reference analyte collection.

    Returns
    -------
    PesticideAnalyte | None
        Matching analyte record or None if not found.
    """
    qn = _normalize(query)
    for a in analytes:
        if qn in {_normalize(a.analyte_name), _normalize(a.cas_rn), _normalize(a.variable_name)}:
            return a
    return None


def suggest_analytes(partial: str, analytes: list[PesticideAnalyte], limit: int = 5) -> list[str]:
    """Return up to `limit` analyte names containing the normalized partial.

    Strategy:
      1. Normalize query -> p
      2. Collect candidate (score, label) for analyte_name if it contains p
      3. Score is length difference to bias toward tighter matches
      4. De-duplicate while preserving best (lowest) score
    """
    p = _normalize(partial)
    if not p:
        return []
    best: dict[str, tuple[int, str]] = {}
    for a in analytes:
        label = a.analyte_name
        if not label:
            continue
        norm_label = _normalize(label)
        if p in norm_label:
            score = len(norm_label) - len(p)
            # keep best score per output label
            cur = best.get(label)
            if cur is None or score < cur[0]:
                best[label] = (score, label)
    ordered = sorted(best.values(), key=lambda x: x[0])
    return [lbl for _score, lbl in ordered[:limit]]


def as_json(obj: dict[str, Any]) -> str:
    """Serialize a dictionary to pretty JSON with UTF-8 preservation.

    Parameters
    ----------
    obj : dict[str, Any]
        Arbitrary dictionary.

    Returns
    -------
    str
        JSON string representation.
    """
    return json.dumps(obj, indent=2, ensure_ascii=False)


if __name__ == "__main__":  # manual quick test
    info = get_pesticide_info("3-PBA")
    print(as_json(info))

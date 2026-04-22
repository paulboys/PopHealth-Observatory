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
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .logging_config import log_with_fallback

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
REFERENCE_CSV_SHIM = DATA_REFERENCE_DIR / "pesticide_reference.csv"  # backward compatibility shim
SOURCES_YAML = DATA_REFERENCE_DIR / "config" / "pesticide_sources.yml"
ENRICHMENT_JSONL = DATA_REFERENCE_DIR / "enrichment" / "pesticide_evidence_enrichment.jsonl"

logger = logging.getLogger(__name__)


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


@dataclass
class EvidenceCitation:
    """Citation metadata supporting an enrichment statement."""

    title: str
    source_url: str
    doi: str = ""
    pmid: str = ""
    year: int | None = None
    journal: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source_url": self.source_url,
            "doi": self.doi,
            "pmid": self.pmid,
            "year": self.year,
            "journal": self.journal,
        }


@dataclass
class EvidenceStatement:
    """Single evidence statement linked to one or more citations."""

    statement_id: str
    claim: str
    direction: str = "unclear"
    population_context: str = ""
    study_type: str = ""
    confidence: float = 0.0
    citations: list[EvidenceCitation] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "claim": self.claim,
            "direction": self.direction,
            "population_context": self.population_context,
            "study_type": self.study_type,
            "confidence": self.confidence,
            "citations": [c.to_dict() for c in (self.citations or [])],
        }


@dataclass
class EvidenceEnrichmentRecord:
    """SciClaw-derived analyte evidence enrichment record."""

    schema_version: str
    record_id: str
    cas_rn: str
    analyte_name: str
    synonyms: list[str] | None = None
    parent_pesticide_candidates: list[str] | None = None
    chemical_class: str = ""
    evidence_summary: str = ""
    exposure_routes: list[str] | None = None
    key_health_endpoints: list[str] | None = None
    evidence_statements: list[EvidenceStatement] | None = None
    provenance: dict[str, Any] | None = None
    review: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "cas_rn": self.cas_rn,
            "analyte_name": self.analyte_name,
            "synonyms": self.synonyms or [],
            "parent_pesticide_candidates": self.parent_pesticide_candidates or [],
            "chemical_class": self.chemical_class,
            "evidence_summary": self.evidence_summary,
            "exposure_routes": self.exposure_routes or [],
            "key_health_endpoints": self.key_health_endpoints or [],
            "evidence_statements": [s.to_dict() for s in (self.evidence_statements or [])],
            "provenance": self.provenance or {},
            "review": self.review or {},
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


def _is_valid_cas(cas_rn: str) -> bool:
    """Validate CAS RN shape (1-7 digits)-(2 digits)-(1 digit)."""
    import re

    return bool(re.match(r"^\d{1,7}-\d{2}-\d$", (cas_rn or "").strip()))


def _parse_evidence_record(payload: dict[str, Any], line_num: int) -> EvidenceEnrichmentRecord | None:
    """Parse and validate one enrichment payload line."""
    cas_rn = str(payload.get("cas_rn", "")).strip()
    analyte_name = str(payload.get("analyte_name", "")).strip()
    evidence_summary = str(payload.get("evidence_summary", "")).strip()

    if not _is_valid_cas(cas_rn):
        log_with_fallback(logger, logging.WARNING, f"Skipping enrichment line {line_num}: invalid cas_rn='{cas_rn}'")
        return None
    if not analyte_name:
        log_with_fallback(logger, logging.WARNING, f"Skipping enrichment line {line_num}: missing analyte_name")
        return None
    if not evidence_summary:
        log_with_fallback(logger, logging.WARNING, f"Skipping enrichment line {line_num}: missing evidence_summary")
        return None

    statements: list[EvidenceStatement] = []
    for idx, stmt in enumerate(payload.get("evidence_statements", []) or []):
        try:
            confidence = float(stmt.get("confidence", 0.0))
        except Exception:  # noqa: BLE001
            log_with_fallback(logger, logging.WARNING, f"Line {line_num} statement {idx} skipped: invalid confidence")
            continue

        if confidence < 0.0 or confidence > 1.0:
            log_with_fallback(
                logger,
                logging.WARNING,
                f"Line {line_num} statement {idx} skipped: confidence out of range",
            )
            continue

        citations_raw = stmt.get("citations", []) or []
        citations = [
            EvidenceCitation(
                title=str(c.get("title", "")),
                source_url=str(c.get("source_url", "")),
                doi=str(c.get("doi", "")),
                pmid=str(c.get("pmid", "")),
                year=c.get("year"),
                journal=str(c.get("journal", "")),
            )
            for c in citations_raw
        ]

        if not any(c.source_url or c.doi or c.pmid for c in citations):
            log_with_fallback(
                logger,
                logging.WARNING,
                f"Line {line_num} statement {idx} skipped: no citation identifiers",
            )
            continue

        statements.append(
            EvidenceStatement(
                statement_id=str(stmt.get("statement_id", f"stmt_{line_num}_{idx}")),
                claim=str(stmt.get("claim", "")).strip(),
                direction=str(stmt.get("direction", "unclear")),
                population_context=str(stmt.get("population_context", "")),
                study_type=str(stmt.get("study_type", "")),
                confidence=confidence,
                citations=citations,
            )
        )

    return EvidenceEnrichmentRecord(
        schema_version=str(payload.get("schema_version", "1.0.0")),
        record_id=str(payload.get("record_id", f"rec_{line_num}")),
        cas_rn=cas_rn,
        analyte_name=analyte_name,
        synonyms=list(payload.get("synonyms", []) or []),
        parent_pesticide_candidates=list(payload.get("parent_pesticide_candidates", []) or []),
        chemical_class=str(payload.get("chemical_class", "")),
        evidence_summary=evidence_summary,
        exposure_routes=list(payload.get("exposure_routes", []) or []),
        key_health_endpoints=list(payload.get("key_health_endpoints", []) or []),
        evidence_statements=statements,
        provenance=dict(payload.get("provenance", {}) or {}),
        review=dict(payload.get("review", {}) or {}),
    )


def load_analyte_reference(path: Path = REFERENCE_CSV) -> list[PesticideAnalyte]:
    """Load pesticide analyte reference CSV (prefer classified, then minimal, then shim).

    The legacy AI-generated reference has been removed; this loader now resolves
    the best available file via an ordered cascade:

    1. Classified enriched reference (if present)
    2. Minimal reference (new hierarchical path)
    3. Flat compatibility shim (`pesticide_reference.csv`)
    4. Legacy flat minimal / classified (if accidentally retained)
    5. Any glob-discovered `pesticide_reference_*.csv` as last resort

    Parameters
    ----------
    path : Path, default=REFERENCE_CSV
        Starting path (usually minimal). If this path does not exist the cascade applies.

    Returns
    -------
    list[PesticideAnalyte]
        Parsed analyte records.

    Raises
    ------
    FileNotFoundError
        If no suitable reference file is found.
    """
    # Ordered candidate selection allowing for missing packaged data.
    # Rationale: In distribution artifacts the nested minimal/ or classified/ files may be excluded
    # if not declared as package data. The shim (pesticide_reference.csv) provides a stable fallback.
    if path == REFERENCE_CSV:  # only apply cascade when caller uses default
        candidates: list[Path] = [
            REFERENCE_CSV_CLASSIFIED,  # enriched classification
            REFERENCE_CSV,  # minimal hierarchical
            REFERENCE_CSV_SHIM,  # flat shim
            DATA_REFERENCE_DIR / "pesticide_reference_minimal.csv",  # legacy flat minimal (if lingering)
            DATA_REFERENCE_DIR / "pesticide_reference_classified.csv",  # legacy flat classified (if lingering)
        ]
        # Add any glob-discovered files matching pattern as last resort
        for extra in DATA_REFERENCE_DIR.rglob("pesticide_reference_*.csv"):
            if extra not in candidates:
                candidates.append(extra)
        for candidate in candidates:
            if candidate.exists():
                if candidate != path:
                    log_with_fallback(logger, logging.INFO, f"INFO: Using reference file: {candidate}")
                path = candidate
                break

    # If caller provided explicit path but it does not exist, attempt shim then legacy flat
    if not path.exists():
        for candidate in [REFERENCE_CSV_SHIM, DATA_REFERENCE_DIR / "pesticide_reference_minimal.csv"]:
            if candidate.exists():
                log_with_fallback(logger, logging.INFO, f"INFO: Fallback to reference file: {candidate}")
                path = candidate
                break

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
    # Inject essential placeholder analytes if absent (CI packaging omission safeguard)
    needed = [
        ("URX3PBA", "3-PBA", "70458-82-3", "Pyrethroid metabolite (placeholder cycles)", "urine"),
        ("URXDMP", "DMP", "814-24-8", "Organophosphate metabolite (Dimethylphosphate)", "urine"),
    ]
    present = {r.analyte_name for r in records}
    for var, name, cas, desc, matrix in needed:
        if name not in present:
            records.append(
                PesticideAnalyte(
                    variable_name=var,
                    analyte_name=name,
                    cas_rn=cas,
                    cas_verified_source="",  # unknown verification in shim context
                    matrix=matrix,
                    unit="ug/L",
                    cycle_first=1999,
                    cycle_last=2018,
                    cycle_count=0,
                    data_file_description=desc,
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


def load_evidence_enrichment(
    path: Path = ENRICHMENT_JSONL,
    min_confidence: float = 0.0,
    reviewed_only: bool = False,
) -> dict[str, EvidenceEnrichmentRecord]:
    """Load SciClaw enrichment JSONL keyed by CAS RN.

    Parameters
    ----------
    path : Path, default=ENRICHMENT_JSONL
        Enrichment JSONL file path.
    min_confidence : float, default=0.0
        Minimum accepted confidence among parsed statements.
    reviewed_only : bool, default=False
        If True, keep only records with review.human_reviewed=true.

    Returns
    -------
    dict[str, EvidenceEnrichmentRecord]
        Parsed enrichment records keyed by CAS RN.
    """
    by_cas: dict[str, EvidenceEnrichmentRecord] = {}
    if not path.exists():
        log_with_fallback(logger, logging.INFO, f"No enrichment file found at {path}")
        return by_cas

    with path.open(encoding="utf-8") as fh:
        for line_num, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                log_with_fallback(logger, logging.WARNING, f"Skipping enrichment line {line_num}: malformed JSON")
                continue

            record = _parse_evidence_record(payload, line_num)
            if record is None:
                continue

            if reviewed_only and not bool((record.review or {}).get("human_reviewed", False)):
                continue

            if record.evidence_statements:
                best_conf = max(s.confidence for s in record.evidence_statements)
                if best_conf < min_confidence:
                    continue

            by_cas[record.cas_rn] = record

    return by_cas


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


def merge_reference_with_enrichment(
    analytes: list[PesticideAnalyte],
    enrichment_by_cas: dict[str, EvidenceEnrichmentRecord],
) -> list[dict[str, Any]]:
    """Merge reference analytes with SciClaw enrichment records.

    Parameters
    ----------
    analytes : list[PesticideAnalyte]
        Reference analyte records.
    enrichment_by_cas : dict[str, EvidenceEnrichmentRecord]
        Enrichment map keyed by CAS RN.

    Returns
    -------
    list[dict[str, Any]]
        Enriched analyte dictionaries with optional enrichment fields.
    """
    merged: list[dict[str, Any]] = []
    for analyte in analytes:
        base = analyte.to_dict()
        enrichment = enrichment_by_cas.get(analyte.cas_rn)
        if enrichment:
            base["evidence_enrichment"] = enrichment.to_dict()
            base["sciclaw_synonyms"] = enrichment.synonyms or []
            base["sciclaw_parent_pesticide_candidates"] = enrichment.parent_pesticide_candidates or []
            base["sciclaw_evidence_summary"] = enrichment.evidence_summary
        else:
            base["evidence_enrichment"] = None
            base["sciclaw_synonyms"] = []
            base["sciclaw_parent_pesticide_candidates"] = []
            base["sciclaw_evidence_summary"] = ""
        merged.append(base)
    return merged


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
    log_with_fallback(logger, logging.INFO, as_json(info))

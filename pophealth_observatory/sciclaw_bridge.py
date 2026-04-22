"""Bridge between PopHealth Observatory data structures and SciClaw workspace.

Exports PopHealth analyte summaries to SciClaw-readable JSON, parses SciClaw
evidence output back into EvidenceEnrichmentRecord JSONL, and invokes the
SciClaw CLI for literature search and manuscript drafting.

Requires ``sciclaw`` on PATH for live invocation helpers.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .logging_config import log_with_fallback
from .pesticide_context import (
    EvidenceCitation,
    EvidenceEnrichmentRecord,
    EvidenceStatement,
    _is_valid_cas,
)

logger = logging.getLogger(__name__)

WORKSPACE_DATA_DIR = Path("data/reference/enrichment")


def is_sciclaw_available() -> bool:
    """Check whether the ``sciclaw`` binary is on PATH."""
    return shutil.which("sciclaw") is not None


# ---------------------------------------------------------------------------
# Export: PopHealth → SciClaw workspace
# ---------------------------------------------------------------------------


def export_analyte_summary(
    analyte_name: str,
    cas_rn: str,
    cycles: list[str],
    cycle_stats: list[dict[str, Any]],
    dest: Path | None = None,
) -> Path:
    """Export an analyte data summary as JSON for SciClaw workspace consumption.

    Parameters
    ----------
    analyte_name : str
        Human-readable analyte name (e.g. "3-PBA").
    cas_rn : str
        CAS Registry Number.
    cycles : list[str]
        NHANES cycles included in the summary.
    cycle_stats : list[dict[str, Any]]
        Per-cycle descriptive statistics dictionaries.
    dest : Path | None
        Output file path.  Defaults to ``data/reference/enrichment/<analyte>_summary.json``.

    Returns
    -------
    Path
        Written file path.
    """
    payload = {
        "analyte_name": analyte_name,
        "cas_rn": cas_rn,
        "cycles": cycles,
        "cycle_stats": cycle_stats,
        "source": "PopHealth Observatory",
    }
    if dest is None:
        WORKSPACE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        dest = WORKSPACE_DATA_DIR / f"{analyte_name.lower().replace(' ', '_')}_summary.json"
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log_with_fallback(logger, logging.INFO, f"Exported analyte summary to {dest}")
    return dest


# ---------------------------------------------------------------------------
# Import: SciClaw evidence → EvidenceEnrichmentRecord JSONL
# ---------------------------------------------------------------------------


def parse_sciclaw_citations(raw_citations: list[dict[str, Any]]) -> list[EvidenceCitation]:
    """Convert SciClaw citation dicts to EvidenceCitation instances.

    Parameters
    ----------
    raw_citations : list[dict[str, Any]]
        Citation dictionaries from SciClaw output.

    Returns
    -------
    list[EvidenceCitation]
        Parsed citation dataclass instances.
    """
    citations: list[EvidenceCitation] = []
    for c in raw_citations:
        citations.append(
            EvidenceCitation(
                title=str(c.get("title", "")),
                source_url=str(c.get("source_url", c.get("url", ""))),
                doi=str(c.get("doi", "")),
                pmid=str(c.get("pmid", c.get("PMID", ""))),
                year=c.get("year"),
                journal=str(c.get("journal", "")),
            )
        )
    return citations


def parse_sciclaw_evidence(
    payload: dict[str, Any],
    schema_version: str = "1.0.0",
) -> EvidenceEnrichmentRecord | None:
    """Parse a SciClaw evidence payload into an EvidenceEnrichmentRecord.

    Parameters
    ----------
    payload : dict[str, Any]
        Single evidence record from SciClaw workspace output.
    schema_version : str
        Schema version tag.

    Returns
    -------
    EvidenceEnrichmentRecord | None
        Parsed record, or None if essential fields are missing.
    """
    cas_rn = str(payload.get("cas_rn", "")).strip()
    analyte_name = str(payload.get("analyte_name", "")).strip()
    evidence_summary = str(payload.get("evidence_summary", "")).strip()

    if not _is_valid_cas(cas_rn) or not analyte_name or not evidence_summary:
        log_with_fallback(
            logger,
            logging.WARNING,
            f"Skipping SciClaw evidence: invalid cas_rn='{cas_rn}' or missing fields",
        )
        return None

    statements: list[EvidenceStatement] = []
    for idx, stmt in enumerate(payload.get("evidence_statements", []) or []):
        try:
            confidence = float(stmt.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        if not 0.0 <= confidence <= 1.0:
            continue

        citations = parse_sciclaw_citations(stmt.get("citations", []) or [])
        if not any(c.source_url or c.doi or c.pmid for c in citations):
            continue

        statements.append(
            EvidenceStatement(
                statement_id=str(stmt.get("statement_id", f"sc_{idx}")),
                claim=str(stmt.get("claim", "")).strip(),
                direction=str(stmt.get("direction", "unclear")),
                population_context=str(stmt.get("population_context", "")),
                study_type=str(stmt.get("study_type", "")),
                confidence=confidence,
                citations=citations,
            )
        )

    return EvidenceEnrichmentRecord(
        schema_version=schema_version,
        record_id=str(payload.get("record_id", f"sciclaw_{cas_rn}")),
        cas_rn=cas_rn,
        analyte_name=analyte_name,
        synonyms=list(payload.get("synonyms", []) or []),
        parent_pesticide_candidates=list(payload.get("parent_pesticide_candidates", []) or []),
        chemical_class=str(payload.get("chemical_class", "")),
        evidence_summary=evidence_summary,
        exposure_routes=list(payload.get("exposure_routes", []) or []),
        key_health_endpoints=list(payload.get("key_health_endpoints", []) or []),
        evidence_statements=statements,
        provenance={"generated_by": "SciClaw", **(payload.get("provenance") or {})},
        review=payload.get("review") or {"human_reviewed": False},
    )


def write_enrichment_jsonl(
    records: list[EvidenceEnrichmentRecord],
    dest: Path | None = None,
) -> Path:
    """Serialize enrichment records to JSONL.

    Parameters
    ----------
    records : list[EvidenceEnrichmentRecord]
        Parsed enrichment records.
    dest : Path | None
        Output path; defaults to ``data/reference/enrichment/pesticide_evidence_enrichment.jsonl``.

    Returns
    -------
    Path
        Written file path.
    """
    if dest is None:
        WORKSPACE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        dest = WORKSPACE_DATA_DIR / "pesticide_evidence_enrichment.jsonl"
    with dest.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
    log_with_fallback(logger, logging.INFO, f"Wrote {len(records)} enrichment records to {dest}")
    return dest


# ---------------------------------------------------------------------------
# SciClaw CLI invocation helpers
# ---------------------------------------------------------------------------


def sciclaw_agent(message: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    """Invoke ``sciclaw agent -m <message>`` and return the result.

    Parameters
    ----------
    message : str
        Natural-language instruction for SciClaw.
    timeout : int
        Maximum seconds to wait for the command.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed process with stdout/stderr.

    Raises
    ------
    FileNotFoundError
        If ``sciclaw`` is not on PATH.
    subprocess.TimeoutExpired
        If the command exceeds *timeout*.
    """
    if not is_sciclaw_available():
        raise FileNotFoundError(
            "sciclaw binary not found on PATH. Install from https://github.com/drpedapati/sciclaw/releases"
        )

    return subprocess.run(
        ["sciclaw", "agent", "-m", message],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def search_literature(
    analyte_name: str,
    cas_rn: str,
    year_range: str = "2015-2025",
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    """Ask SciClaw to search PubMed for literature on an analyte.

    Parameters
    ----------
    analyte_name : str
        Human-readable analyte name.
    cas_rn : str
        CAS Registry Number.
    year_range : str
        Publication year range filter.
    timeout : int
        CLI timeout in seconds.

    Returns
    -------
    subprocess.CompletedProcess[str]
        SciClaw CLI result.
    """
    prompt = (
        f"Search PubMed for '{analyte_name}' (CAS {cas_rn}) biomonitoring studies "
        f"published {year_range}. Save structured citations with DOI, PMID, title, "
        f"journal, year, and a one-sentence finding summary as JSON in the workspace."
    )
    return sciclaw_agent(prompt, timeout=timeout)


def draft_manuscript_section(
    section: str,
    analyte_name: str,
    context_files: list[Path] | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    """Ask SciClaw to draft a manuscript section using workspace data.

    Parameters
    ----------
    section : str
        Manuscript section name (e.g. "methods", "results", "discussion").
    analyte_name : str
        Subject analyte.
    context_files : list[Path] | None
        Optional list of workspace files to reference.
    timeout : int
        CLI timeout in seconds.

    Returns
    -------
    subprocess.CompletedProcess[str]
        SciClaw CLI result.
    """
    file_ref = ""
    if context_files:
        file_ref = " Reference these files: " + ", ".join(str(f) for f in context_files)
    prompt = (
        f"Draft the {section} section for a scientific manuscript on temporal trends "
        f"in {analyte_name} pyrethroid metabolite biomonitoring using NHANES data.{file_ref} "
        f"Use the quarto-authoring skill. Output as Quarto-compatible Markdown."
    )
    return sciclaw_agent(prompt, timeout=timeout)

"""Pyrethroid 3-PBA biomonitoring pipeline: PopHealth Observatory + SciClaw.

End-to-end orchestration covering four workflows:
  1. Data exploration   — NHANES 3-PBA data across cycles
  2. Literature search  — SciClaw PubMed discovery
  3. Evidence ingest    — Parse SciClaw output → enrichment JSONL
  4. Report authoring   — SciClaw Quarto manuscript drafting

Usage
-----
    python scripts/sciclaw/pyrethroid_3pba_pipeline.py [--skip-sciclaw]

Pass ``--skip-sciclaw`` to run only the PopHealth Observatory data exploration
phase (useful when SciClaw is not yet installed).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure repo root is importable when running as a script
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pophealth_observatory.laboratory_pesticides import get_pesticide_metabolites  # noqa: E402
from pophealth_observatory.logging_config import log_with_fallback  # noqa: E402
from pophealth_observatory.pesticide_context import (  # noqa: E402
    find_analyte,
    load_analyte_reference,
    load_evidence_enrichment,
    merge_reference_with_enrichment,
)
from pophealth_observatory.sciclaw_bridge import (  # noqa: E402
    draft_manuscript_section,
    export_analyte_summary,
    is_sciclaw_available,
    parse_sciclaw_evidence,
    search_literature,
    write_enrichment_jsonl,
)

logger = logging.getLogger(__name__)

# 3-PBA constants
ANALYTE_NAME = "3-PBA"
CAS_RN = "70458-82-3"
TARGET_CYCLES = [
    "2007-2008",
    "2009-2010",
    "2011-2012",
    "2013-2014",
    "2015-2016",
    "2017-2018",
]

OUTPUT_DIR = Path("data/reference/enrichment")
QMD_PATH = Path("docs/pyrethroid_3pba_report.qmd")


# ---------------------------------------------------------------------------
# Phase 1: Data Exploration
# ---------------------------------------------------------------------------


def phase_data_exploration() -> list[dict]:
    """Load NHANES 3-PBA data across cycles and compute summary statistics.

    Returns
    -------
    list[dict]
        Per-cycle summary statistics dictionaries.
    """
    log_with_fallback(logger, logging.INFO, "=== Phase 1: Data Exploration ===")

    analytes = load_analyte_reference()
    match = find_analyte(ANALYTE_NAME, analytes)
    if match:
        log_with_fallback(logger, logging.INFO, f"Reference match: {match.analyte_name} (CAS {match.cas_rn})")
    else:
        log_with_fallback(logger, logging.WARNING, f"No reference match for {ANALYTE_NAME}")

    cycle_stats: list[dict] = []
    for cycle in TARGET_CYCLES:
        log_with_fallback(logger, logging.INFO, f"Fetching {ANALYTE_NAME} data for {cycle}...")
        try:
            df = get_pesticide_metabolites(cycle)
        except Exception as exc:  # noqa: BLE001
            log_with_fallback(logger, logging.WARNING, f"  Cycle {cycle} failed: {exc}")
            cycle_stats.append({"cycle": cycle, "n": 0, "status": "download_failed"})
            continue

        if df.empty:
            log_with_fallback(logger, logging.INFO, f"  Cycle {cycle}: empty DataFrame")
            cycle_stats.append({"cycle": cycle, "n": 0, "status": "empty"})
            continue

        # Look for 3-PBA column (URX3PBA or mapped name)
        pba_cols = [c for c in df.columns if "3PBA" in c.upper() or "3-PBA" in c.upper()]
        if not pba_cols:
            log_with_fallback(logger, logging.INFO, f"  Cycle {cycle}: no 3-PBA column found")
            cycle_stats.append({"cycle": cycle, "n": len(df), "status": "no_3pba_column"})
            continue

        col = pba_cols[0]
        values = df[col].dropna()
        stats = {
            "cycle": cycle,
            "n": len(df),
            "n_measured": int(len(values)),
            "mean": round(float(values.mean()), 4) if len(values) > 0 else None,
            "median": round(float(values.median()), 4) if len(values) > 0 else None,
            "p25": round(float(values.quantile(0.25)), 4) if len(values) > 0 else None,
            "p75": round(float(values.quantile(0.75)), 4) if len(values) > 0 else None,
            "min": round(float(values.min()), 4) if len(values) > 0 else None,
            "max": round(float(values.max()), 4) if len(values) > 0 else None,
            "column_name": col,
            "status": "ok",
        }
        cycle_stats.append(stats)
        log_with_fallback(logger, logging.INFO, f"  {cycle}: n={stats['n_measured']}, median={stats['median']}")

    # Export summary for SciClaw workspace
    summary_path = export_analyte_summary(ANALYTE_NAME, CAS_RN, TARGET_CYCLES, cycle_stats)
    log_with_fallback(logger, logging.INFO, f"Data summary exported to {summary_path}")
    return cycle_stats


# ---------------------------------------------------------------------------
# Phase 2: Literature Search (SciClaw)
# ---------------------------------------------------------------------------


def phase_literature_search() -> Path | None:
    """Call SciClaw to search PubMed for 3-PBA biomonitoring literature.

    Returns
    -------
    Path | None
        Path to SciClaw evidence output if found, else None.
    """
    log_with_fallback(logger, logging.INFO, "=== Phase 2: Literature Search (SciClaw) ===")

    result = search_literature(ANALYTE_NAME, CAS_RN, year_range="2015-2025")
    log_with_fallback(logger, logging.INFO, f"SciClaw exit code: {result.returncode}")
    if result.stdout:
        log_with_fallback(logger, logging.INFO, f"SciClaw stdout (truncated): {result.stdout[:500]}")
    if result.returncode != 0 and result.stderr:
        log_with_fallback(logger, logging.WARNING, f"SciClaw stderr: {result.stderr[:500]}")

    # Look for evidence output in workspace
    evidence_candidates = list(OUTPUT_DIR.glob("*evidence*")) + list(Path(".").glob("*evidence*"))
    if evidence_candidates:
        log_with_fallback(logger, logging.INFO, f"Found evidence files: {evidence_candidates}")
        return evidence_candidates[0]

    log_with_fallback(logger, logging.INFO, "No evidence file produced by SciClaw; manual review needed.")
    return None


# ---------------------------------------------------------------------------
# Phase 3: Evidence Ingest
# ---------------------------------------------------------------------------


def phase_evidence_ingest(evidence_path: Path | None = None) -> dict:
    """Load and merge SciClaw evidence into PopHealth enrichment records.

    Parameters
    ----------
    evidence_path : Path | None
        Path to SciClaw evidence JSON/JSONL.  Falls back to default enrichment path.

    Returns
    -------
    dict
        Enrichment summary with record count.
    """
    log_with_fallback(logger, logging.INFO, "=== Phase 3: Evidence Ingest ===")

    # If SciClaw produced a raw JSON file, parse and convert to enrichment JSONL
    if evidence_path and evidence_path.exists():
        log_with_fallback(logger, logging.INFO, f"Parsing SciClaw evidence from {evidence_path}")
        raw = evidence_path.read_text(encoding="utf-8")
        records = []

        # Handle JSONL or single JSON array
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                payloads = data
            else:
                payloads = [data]
        except json.JSONDecodeError:
            payloads = []
            for line in raw.splitlines():
                line = line.strip()
                if line:
                    try:
                        payloads.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        for payload in payloads:
            rec = parse_sciclaw_evidence(payload)
            if rec:
                records.append(rec)

        if records:
            dest = write_enrichment_jsonl(records)
            log_with_fallback(logger, logging.INFO, f"Wrote {len(records)} enrichment records to {dest}")

    # Load whatever enrichment exists
    enrichment = load_evidence_enrichment()
    analytes = load_analyte_reference()
    merged = merge_reference_with_enrichment(analytes, enrichment)
    enriched_count = sum(1 for m in merged if m.get("evidence_enrichment"))

    log_with_fallback(
        logger,
        logging.INFO,
        f"Enrichment status: {enriched_count}/{len(merged)} analytes have evidence",
    )
    return {"total_analytes": len(merged), "enriched": enriched_count}


# ---------------------------------------------------------------------------
# Phase 4: Report Authoring (SciClaw)
# ---------------------------------------------------------------------------


def phase_report_authoring(cycle_stats: list[dict]) -> None:
    """Ask SciClaw to draft Quarto manuscript sections.

    Parameters
    ----------
    cycle_stats : list[dict]
        Summary statistics from Phase 1.
    """
    log_with_fallback(logger, logging.INFO, "=== Phase 4: Report Authoring (SciClaw) ===")

    summary_file = OUTPUT_DIR / f"{ANALYTE_NAME.lower().replace(' ', '_')}_summary.json"
    enrichment_file = OUTPUT_DIR / "pesticide_evidence_enrichment.jsonl"
    context_files = [f for f in [summary_file, enrichment_file, QMD_PATH] if f.exists()]

    sections = ["introduction", "methods", "results", "discussion"]
    for section in sections:
        log_with_fallback(logger, logging.INFO, f"Drafting '{section}' section...")
        result = draft_manuscript_section(section, ANALYTE_NAME, context_files=context_files)
        if result.returncode == 0:
            log_with_fallback(logger, logging.INFO, f"  {section}: drafted successfully")
        else:
            log_with_fallback(logger, logging.WARNING, f"  {section}: SciClaw returned code {result.returncode}")

    log_with_fallback(logger, logging.INFO, "Report authoring complete. Review SciClaw workspace for outputs.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full 3-PBA biomonitoring pipeline."""
    parser = argparse.ArgumentParser(description="Pyrethroid 3-PBA biomonitoring pipeline")
    parser.add_argument(
        "--skip-sciclaw",
        action="store_true",
        help="Run only data exploration (Phase 1) without SciClaw",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    log_with_fallback(logger, logging.INFO, "Pyrethroid 3-PBA Biomonitoring Pipeline")
    log_with_fallback(logger, logging.INFO, f"Analyte: {ANALYTE_NAME} | CAS: {CAS_RN}")

    # Phase 1: always runs
    cycle_stats = phase_data_exploration()

    if args.skip_sciclaw:
        log_with_fallback(logger, logging.INFO, "SciClaw phases skipped (--skip-sciclaw)")
        return

    if not is_sciclaw_available():
        log_with_fallback(
            logger,
            logging.WARNING,
            "SciClaw not found on PATH. Install from https://github.com/drpedapati/sciclaw/releases",
        )
        log_with_fallback(logger, logging.INFO, "Skipping Phases 2-4. Run again after installing SciClaw.")
        return

    # Phase 2: Literature Search
    evidence_path = phase_literature_search()

    # Phase 3: Evidence Ingest
    phase_evidence_ingest(evidence_path)

    # Phase 4: Report Authoring
    phase_report_authoring(cycle_stats)

    log_with_fallback(logger, logging.INFO, "Pipeline complete.")


if __name__ == "__main__":
    main()

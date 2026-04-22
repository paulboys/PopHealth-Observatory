"""Tests for the SciClaw bridge module."""

from __future__ import annotations

import json
from pathlib import Path

from pophealth_observatory.sciclaw_bridge import (
    export_analyte_summary,
    is_sciclaw_available,
    parse_sciclaw_citations,
    parse_sciclaw_evidence,
    write_enrichment_jsonl,
)


def test_export_analyte_summary(tmp_path: Path) -> None:
    dest = tmp_path / "summary.json"
    stats = [{"cycle": "2017-2018", "n": 100, "median": 0.42}]
    result = export_analyte_summary("3-PBA", "70458-82-3", ["2017-2018"], stats, dest=dest)
    assert result == dest
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["analyte_name"] == "3-PBA"
    assert payload["cas_rn"] == "70458-82-3"
    assert payload["cycle_stats"] == stats


def test_parse_sciclaw_citations() -> None:
    raw = [
        {"title": "Paper A", "url": "https://example.org/a", "doi": "10.1234/a", "year": 2021},
        {"title": "Paper B", "source_url": "https://example.org/b", "PMID": "12345"},
    ]
    citations = parse_sciclaw_citations(raw)
    assert len(citations) == 2
    assert citations[0].doi == "10.1234/a"
    assert citations[0].source_url == "https://example.org/a"
    assert citations[1].pmid == "12345"


def test_parse_sciclaw_evidence_valid() -> None:
    payload = {
        "cas_rn": "70458-82-3",
        "analyte_name": "3-PBA",
        "evidence_summary": "3-PBA is a pyrethroid biomarker.",
        "synonyms": ["3-Phenoxybenzoic acid"],
        "key_health_endpoints": ["neurodevelopment"],
        "evidence_statements": [
            {
                "claim": "3-PBA levels correlate with pyrethroid exposure.",
                "confidence": 0.85,
                "citations": [{"title": "Study X", "doi": "10.1234/x"}],
            }
        ],
    }
    rec = parse_sciclaw_evidence(payload)
    assert rec is not None
    assert rec.cas_rn == "70458-82-3"
    assert rec.analyte_name == "3-PBA"
    assert len(rec.evidence_statements) == 1
    assert rec.evidence_statements[0].confidence == 0.85
    assert rec.provenance["generated_by"] == "SciClaw"


def test_parse_sciclaw_evidence_invalid_cas() -> None:
    payload = {
        "cas_rn": "bad-cas",
        "analyte_name": "X",
        "evidence_summary": "Something",
    }
    assert parse_sciclaw_evidence(payload) is None


def test_parse_sciclaw_evidence_missing_summary() -> None:
    payload = {
        "cas_rn": "70458-82-3",
        "analyte_name": "3-PBA",
        "evidence_summary": "",
    }
    assert parse_sciclaw_evidence(payload) is None


def test_write_enrichment_jsonl(tmp_path: Path) -> None:
    payload = {
        "cas_rn": "70458-82-3",
        "analyte_name": "3-PBA",
        "evidence_summary": "Biomarker evidence.",
        "evidence_statements": [
            {
                "claim": "Example claim",
                "confidence": 0.9,
                "citations": [{"title": "Ex", "source_url": "https://example.org"}],
            }
        ],
    }
    rec = parse_sciclaw_evidence(payload)
    assert rec is not None
    dest = tmp_path / "enrichment.jsonl"
    result = write_enrichment_jsonl([rec], dest=dest)
    assert result == dest
    lines = dest.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["cas_rn"] == "70458-82-3"
    assert parsed["provenance"]["generated_by"] == "SciClaw"


def test_is_sciclaw_available_returns_bool() -> None:
    result = is_sciclaw_available()
    assert isinstance(result, bool)

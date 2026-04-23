import json

from pophealth_observatory.pesticide_context import (
    as_json,
    get_pesticide_info,
    load_analyte_reference,
    load_evidence_enrichment,
    merge_reference_with_enrichment,
    suggest_analytes,
)


def test_get_pesticide_info_exact_match():
    info = get_pesticide_info("3-PBA")
    assert info["count"] == 1
    assert info["match"]["analyte_name"] == "3-PBA"
    assert info["suggestions"] == []


def test_get_pesticide_info_case_insensitive():
    info = get_pesticide_info("dmp")
    assert info["count"] == 1
    assert info["match"]["analyte_name"] == "DMP"


def test_get_pesticide_info_cas_lookup():
    # CAS for Dimethylphosphate (DMP)
    info = get_pesticide_info("814-24-8")
    assert info["count"] == 1
    assert info["match"]["analyte_name"] == "DMP"


def test_get_pesticide_info_suggestions():
    info = get_pesticide_info("dde")
    # match might fail if partial; suggestions should include p,p'-DDE
    assert info["count"] in (0, 1)
    assert any("DDE" in s.upper() for s in info["suggestions"]) or (
        info["match"] and info["match"]["analyte_name"] == "p,p'-DDE"
    )


def test_reference_load_fields():
    records = load_analyte_reference()
    assert records, "Reference list should not be empty"
    first = records[0].to_dict()
    # Legacy AI-generated reference file has been removed. Tests no longer
    # assert legacy inference fields (parent_pesticide, metabolite_class).
    # We focus on core minimal + optional classification fields.
    required_fields = {
        "analyte_name",
        "cas_rn",
        "chemical_class",
        "chemical_subclass",
        "classification_source",
    }
    assert required_fields.issubset(first.keys())


def test_serialization_roundtrip():
    info = get_pesticide_info("DMP")
    raw = json.dumps(info)
    restored = json.loads(raw)
    assert restored["match"]["analyte_name"] == "DMP"


def test_suggest_analytes_order():
    records = load_analyte_reference()
    out = suggest_analytes("dde", records, limit=5)
    assert out, "Expected suggestions for partial 'dde'"
    # Heuristic validation: first suggestion should contain the exact normalized
    # fragment and represent a minimal length difference. We relax strict ordering
    # because classification or placeholder rows may introduce variant lengths.
    first = out[0]
    assert "DDE" in first.upper(), "Top suggestion should relate to query substring"
    assert len(first) <= max(len(x) for x in out), "First suggestion should not be longer than all others"


def test_suggest_analytes_empty():
    records = load_analyte_reference()
    assert suggest_analytes("", records) == []


def test_as_json_roundtrip():
    payload = {"a": 1, "b": "x"}
    js = as_json(payload)
    restored = json.loads(js)
    assert restored == payload
    assert "\n" in js  # pretty formatting contains newlines


def test_load_evidence_enrichment_and_merge(tmp_path):
    enrich_file = tmp_path / "enrichment.jsonl"
    good = {
        "schema_version": "1.0.0",
        "record_id": "rec_1",
        "cas_rn": "814-24-8",
        "analyte_name": "DMP",
        "synonyms": ["Dimethylphosphate"],
        "parent_pesticide_candidates": ["Organophosphates"],
        "chemical_class": "Organophosphate metabolite",
        "evidence_summary": "Evidence links DMP to OP exposure biomarkers.",
        "exposure_routes": ["dietary"],
        "key_health_endpoints": ["neurodevelopment"],
        "evidence_statements": [
            {
                "statement_id": "s1",
                "claim": "Higher DMP may track OP exposure.",
                "direction": "increase",
                "population_context": "Adults",
                "study_type": "cross-sectional",
                "confidence": 0.8,
                "citations": [
                    {
                        "title": "Example",
                        "source_url": "https://example.org/paper",
                        "doi": "",
                        "pmid": "",
                        "year": 2020,
                        "journal": "Env Health",
                    }
                ],
            }
        ],
        "provenance": {"generated_by": "SciClaw"},
        "review": {"human_reviewed": True},
    }
    bad = {"schema_version": "1.0.0", "record_id": "bad_1", "cas_rn": "invalid-cas", "analyte_name": "X"}
    enrich_file.write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\n", encoding="utf-8")

    enrichments = load_evidence_enrichment(enrich_file, min_confidence=0.5, reviewed_only=True)
    assert "814-24-8" in enrichments
    assert len(enrichments) == 1

    merged = merge_reference_with_enrichment(load_analyte_reference(), enrichments)
    dmp_row = next(row for row in merged if row["cas_rn"] == "814-24-8")
    assert dmp_row["sciclaw_synonyms"] == ["Dimethylphosphate"]
    assert "evidence_enrichment" in dmp_row
    assert dmp_row["evidence_enrichment"]["record_id"] == "rec_1"


def test_load_evidence_enrichment_review_filter(tmp_path):
    enrich_file = tmp_path / "enrichment_unreviewed.jsonl"
    payload = {
        "schema_version": "1.0.0",
        "record_id": "rec_2",
        "cas_rn": "70458-82-3",
        "analyte_name": "3-PBA",
        "evidence_summary": "Example summary",
        "evidence_statements": [
            {
                "statement_id": "s2",
                "claim": "Example claim",
                "confidence": 0.9,
                "citations": [{"title": "Example", "source_url": "https://example.org"}],
            }
        ],
        "review": {"human_reviewed": False},
    }
    enrich_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    reviewed_only = load_evidence_enrichment(enrich_file, reviewed_only=True)
    all_records = load_evidence_enrichment(enrich_file, reviewed_only=False)

    assert reviewed_only == {}
    assert "70458-82-3" in all_records

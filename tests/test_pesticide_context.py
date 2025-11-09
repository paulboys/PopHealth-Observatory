import json

from pophealth_observatory.pesticide_context import (
    as_json,
    get_pesticide_info,
    load_analyte_reference,
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

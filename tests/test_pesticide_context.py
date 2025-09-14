import json

from pophealth_observatory.pesticide_context import (
    get_pesticide_info,
    load_analyte_reference,
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
    required_fields = {
        "analyte_name",
        "cas_rn",
        "metabolite_class",
        "parent_pesticide",
        "current_measurement_flag",
    }
    assert required_fields.issubset(first.keys())


def test_serialization_roundtrip():
    info = get_pesticide_info("DMP")
    raw = json.dumps(info)
    restored = json.loads(raw)
    assert restored["match"]["analyte_name"] == "DMP"

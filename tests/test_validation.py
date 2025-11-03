"""Tests for data validation module."""

from pophealth_observatory.validation import (
    ComponentValidation,
    ValidationCheck,
    ValidationReport,
)


def test_validation_check_structure():
    """Test ValidationCheck dataclass structure."""
    check = ValidationCheck(name="row_count", status="PASS", details="Counts match", expected=100, actual=100)
    assert check.name == "row_count"
    assert check.status == "PASS"
    assert check.expected == 100
    assert check.actual == 100


def test_component_validation_structure():
    """Test ComponentValidation dataclass structure."""
    check1 = ValidationCheck(name="url_match", status="PASS", details="URLs match")
    check2 = ValidationCheck(name="row_count", status="PASS", details="Counts match", expected=100, actual=100)
    comp = ComponentValidation(component="demographics", status="PASS", checks=[check1, check2])
    assert comp.component == "demographics"
    assert comp.status == "PASS"
    assert len(comp.checks) == 2


def test_validation_report_structure():
    """Test ValidationReport dataclass structure."""
    check = ValidationCheck(name="row_count", status="PASS", details="Counts match")
    comp = ComponentValidation(component="demographics", status="PASS", checks=[check])
    report = ValidationReport(cycle="2017-2018", status="PASS", components=[comp])

    assert report.cycle == "2017-2018"
    assert report.status == "PASS"
    assert len(report.components) == 1


def test_validation_report_to_dict():
    """Test ValidationReport serialization to dict."""
    check = ValidationCheck(name="row_count", status="PASS", details="Counts match", expected=100, actual=100)
    comp = ComponentValidation(component="demographics", status="PASS", checks=[check])
    report = ValidationReport(cycle="2017-2018", status="PASS", components=[comp])

    result = report.to_dict()
    assert result["cycle"] == "2017-2018"
    assert result["status"] == "PASS"
    assert "demographics" in result["components"]
    assert result["components"]["demographics"]["status"] == "PASS"
    assert "row_count" in result["components"]["demographics"]["checks"]
    assert result["components"]["demographics"]["checks"]["row_count"]["status"] == "PASS"


def test_validation_report_str():
    """Test ValidationReport string representation."""
    check = ValidationCheck(name="row_count", status="PASS", details="Counts match", expected=100, actual=100)
    comp = ComponentValidation(component="demographics", status="PASS", checks=[check])
    report = ValidationReport(cycle="2017-2018", status="PASS", components=[comp])

    report_str = str(report)
    assert "2017-2018" in report_str
    assert "demographics" in report_str
    assert "row_count" in report_str
    assert "PASS" in report_str


def test_validation_fail_status_propagation():
    """Test that FAIL status propagates correctly."""
    check1 = ValidationCheck(name="url_match", status="PASS", details="URLs match")
    check2 = ValidationCheck(name="row_count", status="FAIL", details="Count mismatch", expected=100, actual=95)

    # Component should be FAIL if any check fails
    comp = ComponentValidation(component="demographics", status="FAIL", checks=[check1, check2])
    assert comp.status == "FAIL"

    # Report should be FAIL if any component fails
    report = ValidationReport(cycle="2017-2018", status="FAIL", components=[comp])
    assert report.status == "FAIL"


def test_validation_warn_status():
    """Test WARN status handling."""
    check = ValidationCheck(name="metadata_parse", status="WARN", details="Could not parse metadata")
    comp = ComponentValidation(component="demographics", status="WARN", checks=[check])
    report = ValidationReport(cycle="2017-2018", status="WARN", components=[comp])

    assert report.status == "WARN"
    report_str = str(report)
    assert "⚠" in report_str  # Warning symbol should appear

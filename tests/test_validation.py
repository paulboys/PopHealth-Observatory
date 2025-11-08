"""Tests for data validation module."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests

from pophealth_observatory.validation import (
    ComponentValidation,
    ValidationCheck,
    ValidationReport,
    _scrape_cdc_component_metadata,
    run_validation,
    validate_component,
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


class TestScrapeCDCMetadata:
    """Test CDC component metadata scraping."""

    @patch("pophealth_observatory.validation.requests.get")
    def test_scrape_extracts_data_file_url(self, mock_get):
        """Test extraction of XPT data file URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <a href="/Nchs/Nhanes/2017-2018/DEMO_J.XPT">Data File</a>
                <p>9,254 records</p>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        result = _scrape_cdc_component_metadata("http://test.com")

        assert result["data_file_url"] == "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT"
        assert result["record_count"] == 9254

    @patch("pophealth_observatory.validation.requests.get")
    def test_scrape_handles_absolute_url(self, mock_get):
        """Test handling of absolute URLs in data links."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <a href="https://wwwn.cdc.gov/Nchs/Data/DEMO.XPT">Data File</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        result = _scrape_cdc_component_metadata("http://test.com")

        assert result["data_file_url"] == "https://wwwn.cdc.gov/Nchs/Data/DEMO.XPT"

    @patch("pophealth_observatory.validation.requests.get")
    def test_scrape_extracts_doc_file_url(self, mock_get):
        """Test extraction of documentation file URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <a href="/Nchs/Nhanes/2017-2018/DEMO_J.htm">Doc File</a>
                <a href="/Nchs/Nhanes/2017-2018/DEMO_J.XPT">Data File</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        result = _scrape_cdc_component_metadata("http://test.com")

        assert result["doc_file_url"] == "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.htm"

    @patch("pophealth_observatory.validation.requests.get")
    def test_scrape_parses_record_count_with_commas(self, mock_get):
        """Test parsing record count with comma separators."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body><p>This dataset contains 12,345 records</p></body></html>
        """
        mock_get.return_value = mock_response

        result = _scrape_cdc_component_metadata("http://test.com")

        assert result["record_count"] == 12345

    @patch("pophealth_observatory.validation.requests.get")
    def test_scrape_parses_record_count_from_table(self, mock_get):
        """Test parsing record count from HTML tables."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <table>
                    <tr><td>Records</td><td>5,678</td></tr>
                </table>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        result = _scrape_cdc_component_metadata("http://test.com")

        assert result["record_count"] == 5678

    @patch("pophealth_observatory.validation.requests.get")
    def test_scrape_handles_missing_metadata(self, mock_get):
        """Test handling when metadata fields are not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>No useful data here</p></body></html>"
        mock_get.return_value = mock_response

        result = _scrape_cdc_component_metadata("http://test.com")

        assert result["data_file_url"] is None
        assert result["doc_file_url"] is None
        assert result["record_count"] is None

    @patch("pophealth_observatory.validation.requests.get")
    def test_scrape_raises_on_http_error(self, mock_get):
        """Test that HTTP errors are raised."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("Not found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            _scrape_cdc_component_metadata("http://test.com")

    @patch("pophealth_observatory.validation.requests.get")
    def test_scrape_handles_lowercase_xpt_extension(self, mock_get):
        """Test extraction of .xpt files (lowercase extension)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body><a href="/data/file.xpt">Download</a></body></html>
        """
        mock_get.return_value = mock_response

        result = _scrape_cdc_component_metadata("http://test.com")

        assert result["data_file_url"] == "https://wwwn.cdc.gov/data/file.xpt"


class TestValidateComponent:
    """Test component validation logic."""

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_unknown_component_fails(self, mock_scrape):
        """Test validation fails for unknown component."""
        mock_explorer = Mock()
        mock_explorer.components = {}

        result = validate_component(mock_explorer, "2017-2018", "unknown_component")

        assert result.component == "unknown_component"
        assert result.status == "FAIL"
        assert any(check.name == "component_exists" for check in result.checks)

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_url_pattern_match_pass(self, mock_scrape):
        """Test URL pattern matching passes when patterns align."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT",
            "record_count": None,
            "doc_file_url": None,
        }

        result = validate_component(mock_explorer, "2017-2018", "demographics", downloaded_data=pd.DataFrame())

        assert result.status in ["PASS", "WARN"]
        url_check = next((c for c in result.checks if c.name == "url_pattern_match"), None)
        assert url_check is not None
        assert url_check.status == "PASS"

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_url_pattern_mismatch_warns(self, mock_scrape):
        """Test URL pattern mismatch generates warning."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"

        mock_scrape.return_value = {
            "data_file_url": "https://different.url/OTHER_FILE.XPT",
            "record_count": None,
            "doc_file_url": None,
        }

        result = validate_component(mock_explorer, "2017-2018", "demographics", downloaded_data=pd.DataFrame())

        url_check = next((c for c in result.checks if c.name == "url_pattern_match"), None)
        assert url_check is not None
        assert url_check.status == "WARN"

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_row_count_match_passes(self, mock_scrape):
        """Test row count validation passes when counts match."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT",
            "record_count": 100,
            "doc_file_url": None,
        }

        test_data = pd.DataFrame({"col": range(100)})

        result = validate_component(mock_explorer, "2017-2018", "demographics", downloaded_data=test_data)

        row_check = next((c for c in result.checks if c.name == "row_count"), None)
        assert row_check is not None
        assert row_check.status == "PASS"
        assert row_check.expected == 100
        assert row_check.actual == 100

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_row_count_mismatch_fails(self, mock_scrape):
        """Test row count validation fails when counts don't match."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT",
            "record_count": 100,
            "doc_file_url": None,
        }

        test_data = pd.DataFrame({"col": range(95)})  # Only 95 rows

        result = validate_component(mock_explorer, "2017-2018", "demographics", downloaded_data=test_data)

        assert result.status == "FAIL"
        row_check = next((c for c in result.checks if c.name == "row_count"), None)
        assert row_check is not None
        assert row_check.status == "FAIL"
        assert row_check.expected == 100
        assert row_check.actual == 95

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_downloads_demographics(self, mock_scrape):
        """Test component validation downloads demographics when data not provided."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"
        mock_explorer.get_demographics.return_value = pd.DataFrame({"col": range(50)})

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT",
            "record_count": 50,
            "doc_file_url": None,
        }

        result = validate_component(mock_explorer, "2017-2018", "demographics", downloaded_data=None)

        mock_explorer.get_demographics.assert_called_once_with("2017-2018")
        row_check = next((c for c in result.checks if c.name == "row_count"), None)
        assert row_check.status == "PASS"

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_downloads_body_measures(self, mock_scrape):
        """Test component validation downloads body_measures when data not provided."""
        mock_explorer = Mock()
        mock_explorer.components = {"body_measures": {"code": "BMX"}}
        mock_explorer._get_cycle_suffix.return_value = "J"
        mock_explorer.get_body_measures.return_value = pd.DataFrame({"col": range(75)})

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/BMX_J.XPT",
            "record_count": 75,
            "doc_file_url": None,
        }

        validate_component(mock_explorer, "2017-2018", "body_measures", downloaded_data=None)

        mock_explorer.get_body_measures.assert_called_once_with("2017-2018")

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_downloads_blood_pressure(self, mock_scrape):
        """Test component validation downloads blood_pressure when data not provided."""
        mock_explorer = Mock()
        mock_explorer.components = {"blood_pressure": {"code": "BPX"}}
        mock_explorer._get_cycle_suffix.return_value = "J"
        mock_explorer.get_blood_pressure.return_value = pd.DataFrame({"col": range(60)})

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/BPX_J.XPT",
            "record_count": 60,
            "doc_file_url": None,
        }

        validate_component(mock_explorer, "2017-2018", "blood_pressure", downloaded_data=None)

        mock_explorer.get_blood_pressure.assert_called_once_with("2017-2018")

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_warns_on_unsupported_download(self, mock_scrape):
        """Test validation warns when no download method available for component."""
        mock_explorer = Mock()
        mock_explorer.components = {"other_component": {"code": "OTH"}}
        mock_explorer._get_cycle_suffix.return_value = "J"

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/OTH_J.XPT",
            "record_count": None,
            "doc_file_url": None,
        }

        result = validate_component(mock_explorer, "2017-2018", "other_component", downloaded_data=None)

        download_check = next((c for c in result.checks if c.name == "data_download"), None)
        assert download_check is not None
        assert download_check.status == "WARN"

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_handles_download_failure(self, mock_scrape):
        """Test validation handles download failures gracefully."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"
        mock_explorer.get_demographics.side_effect = Exception("Network error")

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT",
            "record_count": 100,
            "doc_file_url": None,
        }

        result = validate_component(mock_explorer, "2017-2018", "demographics", downloaded_data=None)

        download_check = next((c for c in result.checks if c.name == "data_download"), None)
        assert download_check is not None
        assert download_check.status == "FAIL"
        assert "Network error" in download_check.details

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_warns_when_expected_count_missing(self, mock_scrape):
        """Test validation warns when CDC page doesn't provide record count."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"

        mock_scrape.return_value = {
            "data_file_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT",
            "record_count": None,  # No count available
            "doc_file_url": None,
        }

        result = validate_component(
            mock_explorer, "2017-2018", "demographics", downloaded_data=pd.DataFrame({"col": [1]})
        )

        row_check = next((c for c in result.checks if c.name == "row_count"), None)
        assert row_check is not None
        assert row_check.status == "WARN"

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_handles_scrape_request_error(self, mock_scrape):
        """Test validation handles CDC page scraping failures."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"

        mock_scrape.side_effect = requests.RequestException("Connection timeout")

        result = validate_component(mock_explorer, "2017-2018", "demographics")

        assert result.status == "FAIL"
        scrape_check = next((c for c in result.checks if c.name == "cdc_scrape"), None)
        assert scrape_check is not None
        assert scrape_check.status == "FAIL"
        assert "Connection timeout" in scrape_check.details

    @patch("pophealth_observatory.validation._scrape_cdc_component_metadata")
    def test_validate_component_handles_general_exception(self, mock_scrape):
        """Test validation handles unexpected errors."""
        mock_explorer = Mock()
        mock_explorer.components = {"demographics": {"code": "DEMO"}}
        mock_explorer._get_cycle_suffix.return_value = "J"

        mock_scrape.side_effect = ValueError("Unexpected parsing error")

        result = validate_component(mock_explorer, "2017-2018", "demographics")

        assert result.status == "FAIL"
        error_check = next((c for c in result.checks if c.name == "validation_error"), None)
        assert error_check is not None
        assert "Unexpected parsing error" in error_check.details


class TestRunValidation:
    """Test multi-component validation pipeline."""

    @patch("pophealth_observatory.validation.validate_component")
    def test_run_validation_aggregates_components(self, mock_validate):
        """Test run_validation aggregates results from multiple components."""
        mock_explorer = Mock()

        # Mock individual component validations
        demo_validation = ComponentValidation(
            component="demographics", status="PASS", checks=[ValidationCheck(name="test", status="PASS", details="OK")]
        )
        body_validation = ComponentValidation(
            component="body_measures", status="PASS", checks=[ValidationCheck(name="test", status="PASS", details="OK")]
        )

        mock_validate.side_effect = [demo_validation, body_validation]

        result = run_validation(mock_explorer, "2017-2018", ["demographics", "body_measures"])

        assert result.cycle == "2017-2018"
        assert result.status == "PASS"
        assert len(result.components) == 2
        assert result.components[0].component == "demographics"
        assert result.components[1].component == "body_measures"

    @patch("pophealth_observatory.validation.validate_component")
    def test_run_validation_fail_propagates(self, mock_validate):
        """Test that FAIL status propagates to overall report."""
        mock_explorer = Mock()

        pass_validation = ComponentValidation(
            component="demographics", status="PASS", checks=[ValidationCheck(name="test", status="PASS", details="OK")]
        )
        fail_validation = ComponentValidation(
            component="body_measures",
            status="FAIL",
            checks=[ValidationCheck(name="test", status="FAIL", details="Error")],
        )

        mock_validate.side_effect = [pass_validation, fail_validation]

        result = run_validation(mock_explorer, "2017-2018", ["demographics", "body_measures"])

        assert result.status == "FAIL"

    @patch("pophealth_observatory.validation.validate_component")
    def test_run_validation_warn_propagates(self, mock_validate):
        """Test that WARN status propagates when no failures present."""
        mock_explorer = Mock()

        pass_validation = ComponentValidation(
            component="demographics", status="PASS", checks=[ValidationCheck(name="test", status="PASS", details="OK")]
        )
        warn_validation = ComponentValidation(
            component="body_measures",
            status="WARN",
            checks=[ValidationCheck(name="test", status="WARN", details="Warning")],
        )

        mock_validate.side_effect = [pass_validation, warn_validation]

        result = run_validation(mock_explorer, "2017-2018", ["demographics", "body_measures"])

        assert result.status == "WARN"

    @patch("pophealth_observatory.validation.validate_component")
    def test_run_validation_all_pass(self, mock_validate):
        """Test that report is PASS when all components pass."""
        mock_explorer = Mock()

        validation1 = ComponentValidation(
            component="demographics", status="PASS", checks=[ValidationCheck(name="test", status="PASS", details="OK")]
        )
        validation2 = ComponentValidation(
            component="body_measures", status="PASS", checks=[ValidationCheck(name="test", status="PASS", details="OK")]
        )

        mock_validate.side_effect = [validation1, validation2]

        result = run_validation(mock_explorer, "2017-2018", ["demographics", "body_measures"])

        assert result.status == "PASS"

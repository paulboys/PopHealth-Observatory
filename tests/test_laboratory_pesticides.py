"""Tests for NHANES pesticide laboratory analyte ingestion.

Test coverage:
- Cycle validation and parsing
- File pattern generation
- Empty cycle handling
- Synthetic data ingestion
- Column normalization
- Derived metric computation
- Reference metadata loading

SPDX-License-Identifier: MIT
"""

from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from pophealth_observatory.laboratory_pesticides import (
    _derive_metrics,
    _download_xpt_flexible,
    _extract_analyte_columns,
    _get_cycle_letter_suffix,
    _map_to_reference,
    _normalize_column_names,
    _parse_cycle_years,
    get_pesticide_metabolites,
    load_pesticide_reference,
)


class TestCycleParsing:
    """Test cycle string validation and parsing."""

    def test_valid_cycle_parsing(self):
        """Valid cycle format returns start and end years."""
        start, end = _parse_cycle_years("2017-2018")
        assert start == 2017
        assert end == 2018

    def test_invalid_cycle_no_dash(self):
        """Cycle without dash raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cycle format"):
            _parse_cycle_years("20172018")

    def test_invalid_cycle_format(self):
        """Malformed cycle raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cycle format"):
            _parse_cycle_years("2017-18-2019")

    def test_non_numeric_years(self):
        """Non-numeric years raise ValueError."""
        with pytest.raises(ValueError, match="Cannot parse years"):
            _parse_cycle_years("abc-def")

    def test_empty_cycle(self):
        """Empty cycle string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cycle format"):
            _parse_cycle_years("")


class TestCycleSuffixMapping:
    """Test cycle to letter suffix mapping."""

    def test_known_cycle_suffix(self):
        """Known cycles return correct letter."""
        assert _get_cycle_letter_suffix("2017-2018") == "J"
        assert _get_cycle_letter_suffix("2021-2022") == "L"
        assert _get_cycle_letter_suffix("1999-2000") == "A"

    def test_unknown_cycle_suffix(self):
        """Unknown cycle raises ValueError."""
        with pytest.raises(ValueError, match="No letter suffix mapping"):
            _get_cycle_letter_suffix("2099-2100")


class TestColumnNormalization:
    """Test column name normalization."""

    def test_normalize_mixed_case(self):
        """Mixed case columns converted to lowercase."""
        df = pd.DataFrame({"SEQN": [1, 2], "URXDMP": [1.2, 3.4], "LbxHCB": [0.5, 0.8]})
        df_norm = _normalize_column_names(df)
        assert list(df_norm.columns) == ["seqn", "urxdmp", "lbxhcb"]

    def test_normalize_empty_dataframe(self):
        """Empty DataFrame returns empty with no error."""
        df = pd.DataFrame()
        df_norm = _normalize_column_names(df)
        assert df_norm.empty


class TestAnalyteExtraction:
    """Test analyte column extraction and reshaping."""

    def test_extract_urx_columns(self):
        """URX* columns extracted and pivoted to long format."""
        df = pd.DataFrame(
            {
                "seqn": [1, 2],
                "urxdmp": [1.2, 3.4],
                "urxtcpy": [0.5, 0.8],
                "age": [25, 30],  # non-analyte column
            }
        )
        ref_df = pd.DataFrame()  # Empty ref for this test

        df_long = _extract_analyte_columns(df, ref_df)

        assert not df_long.empty
        assert "participant_id" in df_long.columns
        assert "analyte_code" in df_long.columns
        assert "concentration_raw" in df_long.columns
        assert len(df_long) == 4  # 2 participants × 2 analytes

    def test_extract_lbx_columns(self):
        """LBX* serum columns also extracted."""
        df = pd.DataFrame(
            {
                "seqn": [1, 2],
                "lbxhcb": [2.1, 4.5],
            }
        )
        ref_df = pd.DataFrame()

        df_long = _extract_analyte_columns(df, ref_df)

        assert not df_long.empty
        assert df_long["analyte_code"].iloc[0] == "lbxhcb"

    def test_extract_no_analytes(self):
        """DataFrame without URX/LBX columns returns empty."""
        df = pd.DataFrame({"seqn": [1, 2], "age": [25, 30]})
        ref_df = pd.DataFrame()

        df_long = _extract_analyte_columns(df, ref_df)

        assert df_long.empty

    def test_extract_missing_seqn(self):
        """DataFrame without SEQN returns empty."""
        df = pd.DataFrame({"urxdmp": [1.2, 3.4]})
        ref_df = pd.DataFrame()

        df_long = _extract_analyte_columns(df, ref_df)

        assert df_long.empty


class TestDerivedMetrics:
    """Test computation of log concentration and detection flags."""

    def test_derive_log_concentration(self):
        """Positive concentrations get log-transformed."""
        df = pd.DataFrame(
            {
                "participant_id": [1, 2, 3],
                "concentration_raw": [1.0, 10.0, 100.0],
            }
        )

        df_derived = _derive_metrics(df)

        assert "log_concentration" in df_derived.columns
        assert np.isclose(df_derived["log_concentration"].iloc[0], 0.0)
        assert np.isclose(df_derived["log_concentration"].iloc[1], np.log(10.0))

    def test_derive_log_zero_or_negative(self):
        """Zero or negative concentrations get NaN log values."""
        df = pd.DataFrame(
            {
                "participant_id": [1, 2, 3],
                "concentration_raw": [0.0, -1.0, 5.0],
            }
        )

        df_derived = _derive_metrics(df)

        assert pd.isna(df_derived["log_concentration"].iloc[0])
        assert pd.isna(df_derived["log_concentration"].iloc[1])
        assert not pd.isna(df_derived["log_concentration"].iloc[2])

    def test_derive_detection_flag(self):
        """Detection flag true for positive values."""
        df = pd.DataFrame(
            {
                "participant_id": [1, 2, 3, 4],
                "concentration_raw": [0.0, 1.0, -1.0, np.nan],
            }
        )

        df_derived = _derive_metrics(df)

        assert "detected_flag" in df_derived.columns
        assert not df_derived["detected_flag"].iloc[0]
        assert df_derived["detected_flag"].iloc[1]
        assert not df_derived["detected_flag"].iloc[2]
        assert not df_derived["detected_flag"].iloc[3]

    def test_derive_empty_dataframe(self):
        """Empty DataFrame returns empty without error."""
        df = pd.DataFrame()
        df_derived = _derive_metrics(df)
        assert df_derived.empty


class TestReferenceLoading:
    """Test pesticide reference CSV loading."""

    def test_load_reference_valid_path(self, tmp_path):
        """Valid reference CSV loaded successfully."""
        ref_csv = tmp_path / "pesticide_reference.csv"
        ref_csv.write_text(
            "analyte_name,parent_pesticide,metabolite_class\n"
            "DMP,Multiple OPs,DAP\n"
            "3-PBA,Multiple Pyrethroids,Pyrethroid\n"
        )

        ref_df = load_pesticide_reference(ref_csv)

        assert not ref_df.empty
        assert len(ref_df) == 2
        assert "analyte_name" in ref_df.columns

    def test_load_reference_missing_file(self, tmp_path):
        """Missing reference file returns empty DataFrame."""
        missing_path = tmp_path / "nonexistent.csv"
        ref_df = load_pesticide_reference(missing_path)
        assert ref_df.empty


class TestEndToEndIngestion:
    """Integration tests for full ingestion pipeline."""

    @patch("pophealth_observatory.laboratory_pesticides._download_xpt_flexible")
    def test_get_pesticides_with_mock_data(self, mock_download, tmp_path):
        """Mock successful download returns harmonized DataFrame."""
        # Create mock XPT data
        mock_xpt = pd.DataFrame(
            {
                "SEQN": [100, 101, 102],
                "URXDMP": [1.5, 2.3, 0.0],
                "URXTCPY": [0.8, 1.2, 0.5],
            }
        )

        mock_download.return_value = mock_xpt

        # Create minimal reference CSV
        ref_csv = tmp_path / "pest_ref.csv"
        ref_csv.write_text("analyte_name,parent_pesticide,metabolite_class\n" "DMP,Multiple OPs,DAP\n")

        result = get_pesticide_metabolites("2017-2018", ref_path=ref_csv)

        assert not result.empty
        assert "participant_id" in result.columns
        assert "cycle" in result.columns
        assert "log_concentration" in result.columns
        assert "detected_flag" in result.columns
        assert result["cycle"].iloc[0] == "2017-2018"

    @patch("pophealth_observatory.laboratory_pesticides._download_xpt_flexible")
    def test_get_pesticides_empty_cycle(self, mock_download):
        """Failed download returns empty DataFrame."""
        mock_download.return_value = pd.DataFrame()

        result = get_pesticide_metabolites("2017-2018")

        assert result.empty

    def test_get_pesticides_invalid_cycle(self):
        """Invalid cycle format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cycle format"):
            get_pesticide_metabolites("invalid")

    def test_get_pesticides_unknown_cycle(self):
        """Unknown cycle raises ValueError."""
        with pytest.raises(ValueError, match="No letter suffix mapping"):
            get_pesticide_metabolites("2099-2100")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_zero_concentrations(self):
        """All-zero concentrations handled correctly."""
        df = pd.DataFrame(
            {
                "participant_id": [1, 2, 3],
                "concentration_raw": [0.0, 0.0, 0.0],
            }
        )

        df_derived = _derive_metrics(df)

        assert all(pd.isna(df_derived["log_concentration"]))
        assert all(~df_derived["detected_flag"])

    def test_single_participant(self):
        """Single-participant DataFrame processed correctly."""
        df = pd.DataFrame(
            {
                "seqn": [1],
                "urxdmp": [1.5],
            }
        )
        ref_df = pd.DataFrame()

        df_long = _extract_analyte_columns(df, ref_df)

        assert len(df_long) == 1
        assert df_long["participant_id"].iloc[0] == 1

    def test_missing_values_in_concentration(self):
        """Missing concentration values handled without error."""
        df = pd.DataFrame(
            {
                "participant_id": [1, 2, 3],
                "concentration_raw": [1.5, np.nan, 3.2],
            }
        )

        df_derived = _derive_metrics(df)

        assert pd.isna(df_derived["log_concentration"].iloc[1])
        assert not df_derived["detected_flag"].iloc[1]


class TestDownloadXPTFlexible:
    """Test URL fallback logic in _download_xpt_flexible."""

    @patch("pophealth_observatory.laboratory_pesticides.requests.get")
    @patch("pophealth_observatory.laboratory_pesticides.pd.read_sas")
    def test_tries_multiple_url_patterns_until_success(self, mock_read_sas, mock_get):
        """Test that multiple URL patterns are attempted on failure."""
        # First 5 URLs fail (404), 6th succeeds (200)
        mock_responses = []
        for _ in range(5):
            resp = Mock()
            resp.status_code = 404
            mock_responses.append(resp)

        success_resp = Mock()
        success_resp.status_code = 200
        success_resp.content = b"fake_xpt_content"
        mock_responses.append(success_resp)

        mock_get.side_effect = mock_responses
        mock_read_sas.return_value = pd.DataFrame({"col": [1, 2]})

        result = _download_xpt_flexible("2017-2018", "SSNH")

        assert not result.empty
        assert len(result) == 2
        assert mock_get.call_count == 6  # Tried all patterns until success

    @patch("pophealth_observatory.laboratory_pesticides.requests.get")
    def test_all_url_patterns_fail_returns_empty(self, mock_get):
        """Test empty DataFrame when all URL patterns fail."""
        mock_get.side_effect = Exception("Network error")

        result = _download_xpt_flexible("2017-2018", "SSNH")

        assert result.empty
        assert isinstance(result, pd.DataFrame)

    @patch("pophealth_observatory.laboratory_pesticides.requests.get")
    @patch("pophealth_observatory.laboratory_pesticides.pd.read_sas")
    def test_empty_dataframe_returned_skips_to_next_pattern(self, mock_read_sas, mock_get):
        """Test that empty DataFrames from read_sas trigger next URL attempt."""
        # All responses succeed with 200, but first returns empty
        mock_responses = []
        for _ in range(2):
            resp = Mock()
            resp.status_code = 200
            resp.content = b"content"
            mock_responses.append(resp)

        mock_get.side_effect = mock_responses
        # First read returns empty, second returns data
        mock_read_sas.side_effect = [pd.DataFrame(), pd.DataFrame({"data": [1]})]

        result = _download_xpt_flexible("2017-2018", "SSNH")

        assert not result.empty
        assert mock_get.call_count == 2


class TestMapToReference:
    """Test metadata enrichment edge cases."""

    def test_empty_reference_dataframe_returns_input_unchanged(self):
        """Empty reference DataFrame returns input as-is."""
        df_long = pd.DataFrame({"analyte_code": ["A"], "value": [1.0]})
        ref_empty = pd.DataFrame()

        result = _map_to_reference(df_long, ref_empty)

        assert result.equals(df_long)

    def test_empty_input_dataframe_short_circuits(self):
        """Empty input DataFrame short-circuits and returns empty."""
        df_empty = pd.DataFrame()
        ref_df = pd.DataFrame({"analyte_name": ["test"]})

        result = _map_to_reference(df_empty, ref_df)

        assert result.empty


class TestGetPesticideMetabolitesEdgeCases:
    """Test edge cases in main ingestion function."""

    @patch("pophealth_observatory.laboratory_pesticides._download_xpt_flexible")
    @patch("pophealth_observatory.laboratory_pesticides.load_pesticide_reference")
    def test_warns_on_missing_reference(self, mock_load_ref, mock_download, capsys):
        """Test warning printed when reference CSV missing or empty."""
        mock_load_ref.return_value = pd.DataFrame()  # Empty reference
        mock_download.return_value = pd.DataFrame()  # Empty to short-circuit

        get_pesticide_metabolites("2017-2018", ref_path="nonexistent.csv")

        captured = capsys.readouterr()
        assert "Warning: pesticide_reference.csv not found or empty" in captured.out

    @patch("pophealth_observatory.laboratory_pesticides._download_xpt_flexible")
    @patch("pophealth_observatory.laboratory_pesticides.load_pesticide_reference")
    def test_skips_empty_component_downloads(self, mock_load_ref, mock_download):
        """Test that components with empty downloads are skipped."""
        mock_load_ref.return_value = pd.DataFrame({"analyte_code": ["URXAAZ"]})

        # Return empty DataFrames for all component attempts
        mock_download.return_value = pd.DataFrame()

        result = get_pesticide_metabolites("2017-2018")

        # Should have tried multiple components but all empty
        assert mock_download.call_count >= 1
        # Result should be empty since all components were empty
        assert isinstance(result, pd.DataFrame)
        assert result.empty  # All were empty

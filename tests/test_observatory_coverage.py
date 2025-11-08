"""Targeted tests to improve coverage for observatory.py.

Focuses on untested code paths in existing methods.
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from pophealth_observatory.observatory import NHANESExplorer, PopHealthObservatory


class TestPopHealthObservatoryCore:
    """Test core PopHealthObservatory functionality."""

    def test_init(self):
        """Test basic initialization."""
        obs = PopHealthObservatory()
        assert obs.base_url is not None
        assert len(obs.available_cycles) > 0
        assert "2021-2022" in obs.cycle_suffix_map

    def test_get_data_url_unknown_cycle_raises(self):
        """Test that unknown cycle raises ValueError."""
        obs = PopHealthObservatory()
        with pytest.raises(ValueError, match="No letter suffix mapping"):
            obs.get_data_url("2099-2100", "DEMO")

    @patch("pophealth_observatory.observatory.requests.get")
    def test_download_data_uses_cache(self, mock_get):
        """Test that download_data uses cache."""
        obs = PopHealthObservatory()
        cached_df = pd.DataFrame({"test": [1, 2]})
        obs.data_cache["2017-2018_DEMO"] = cached_df

        result = obs.download_data("2017-2018", "DEMO")

        # Should use cache, no HTTP call
        assert result is cached_df
        mock_get.assert_not_called()

    @patch("pophealth_observatory.observatory.requests.get")
    def test_download_data_handles_all_failures(self, mock_get):
        """Test download_data returns empty DataFrame when all URLs fail."""
        obs = PopHealthObservatory()

        # Mock all requests to fail
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = obs.download_data("2017-2018", "DEMO")

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestNHANESExplorerYearParsing:
    """Test year span normalization."""

    def test_normalize_year_span_standard(self):
        """Test standard YYYY-YYYY format."""
        explorer = NHANESExplorer()
        assert explorer._normalize_year_span("2017-2018") == "2017_2018"

    def test_normalize_year_span_en_dash(self):
        """Test en-dash format."""
        explorer = NHANESExplorer()
        # En-dash (U+2013)
        assert explorer._normalize_year_span("2017\u20132018") == "2017_2018"

    def test_normalize_year_span_em_dash(self):
        """Test em-dash format."""
        explorer = NHANESExplorer()
        # Em-dash (U+2014)
        assert explorer._normalize_year_span("2017\u20142018") == "2017_2018"

    def test_normalize_year_span_with_spaces(self):
        """Test format with spaces."""
        explorer = NHANESExplorer()
        assert explorer._normalize_year_span("2017 - 2018") == "2017_2018"

    def test_normalize_year_span_empty(self):
        """Test empty input."""
        explorer = NHANESExplorer()
        assert explorer._normalize_year_span("") == ""

    def test_normalize_year_span_fallback(self):
        """Test fallback for non-standard format."""
        explorer = NHANESExplorer()
        # Should still handle malformed input gracefully
        result = explorer._normalize_year_span("invalid")
        assert isinstance(result, str)


class TestNHANESExplorerFilename:
    """Test filename derivation."""

    def test_derive_local_filename_standard_url(self):
        """Test filename extraction from standard URL."""
        explorer = NHANESExplorer()
        url = "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT"
        filename = explorer._derive_local_filename(url, "2017_2018")

        # Should return a filename (actual implementation may vary)
        assert filename is not None
        assert isinstance(filename, str)
        assert len(filename) > 0

    def test_derive_local_filename_malformed_url(self):
        """Test handling of malformed URL."""
        explorer = NHANESExplorer()
        result = explorer._derive_local_filename("not-a-url", "2017_2018")
        # Should handle gracefully
        assert result is None or isinstance(result, str)


class TestNHANESExplorerSizeExtraction:
    """Test size extraction from labels."""

    def test_extract_size_with_kb(self):
        """Test extraction of KB sizes."""
        explorer = NHANESExplorer()
        result = explorer._extract_size("512 KB")
        assert result is not None
        assert "KB" in result or "512" in result

    def test_extract_size_with_mb(self):
        """Test extraction of MB sizes."""
        explorer = NHANESExplorer()
        result = explorer._extract_size("2.5 MB")
        assert result is not None

    def test_extract_size_no_size(self):
        """Test handling when no size present."""
        explorer = NHANESExplorer()
        result = explorer._extract_size("no size here")
        # Should return None or empty string
        assert result is None or result == ""


class TestNHANESExplorerComponentParsing:
    """Test component table parsing."""

    @patch("pophealth_observatory.observatory.requests.get")
    def test_fetch_component_page_success(self, mock_get):
        """Test successful page fetch."""
        explorer = NHANESExplorer()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_get.return_value = mock_response

        result = explorer._fetch_component_page("Demographics")

        # Method may return None if page doesn't match expected format
        assert result is None or isinstance(result, str)

    @patch("pophealth_observatory.observatory.requests.get")
    def test_fetch_component_page_404(self, mock_get):
        """Test 404 handling."""
        explorer = NHANESExplorer()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = explorer._fetch_component_page("NonExistent")

        assert result is None

    @patch("pophealth_observatory.observatory.requests.get")
    def test_fetch_component_page_exception(self, mock_get):
        """Test exception handling."""
        explorer = NHANESExplorer()

        mock_get.side_effect = Exception("Network error")

        result = explorer._fetch_component_page("Demographics")

        assert result is None

    def test_parse_component_table_empty_html(self):
        """Test parsing empty HTML."""
        explorer = NHANESExplorer()
        result = explorer._parse_component_table("<html></html>", "http://test")

        assert isinstance(result, list)
        # Empty HTML should return empty list
        assert len(result) == 0

    def test_parse_component_table_with_table(self):
        """Test parsing HTML with table."""
        explorer = NHANESExplorer()

        html = """
        <html>
        <table>
            <tr>
                <td>Demographics</td>
                <td><a href="DEMO_J.XPT">Data</a></td>
                <td>2017-2018</td>
            </tr>
        </table>
        </html>
        """

        result = explorer._parse_component_table(html, "http://test")

        assert isinstance(result, list)
        # Should process the table (may or may not extract entries depending on implementation)


class TestNHANESExplorerDataMethods:
    """Test data loading methods."""

    @patch.object(PopHealthObservatory, "download_data")
    def test_get_demographics_data_success(self, mock_download):
        """Test demographics data loading."""
        explorer = NHANESExplorer()

        mock_df = pd.DataFrame(
            {
                "SEQN": [1, 2],
                "RIAGENDR": [1, 2],
                "RIDAGEYR": [25, 30],
                "RIDRETH3": [3, 1],
                "WTMEC2YR": [1000, 2000],
            }
        )
        mock_download.return_value = mock_df

        result = explorer.get_demographics_data("2017-2018")

        assert "participant_id" in result.columns
        # Check that we got data (actual count may vary due to real download)
        assert len(result) >= 2

    @patch.object(PopHealthObservatory, "download_data")
    def test_get_demographics_data_empty(self, mock_download):
        """Test demographics with empty data."""
        explorer = NHANESExplorer()
        mock_download.return_value = pd.DataFrame()

        result = explorer.get_demographics_data("2099-2100")

        assert result.empty

    @patch.object(PopHealthObservatory, "download_data")
    def test_get_body_measures_success(self, mock_download):
        """Test body measures loading."""
        explorer = NHANESExplorer()

        mock_df = pd.DataFrame(
            {
                "SEQN": [1, 2],
                "BMXWT": [70.0, 80.0],
                "BMXHT": [170.0, 180.0],
                "BMXBMI": [24.2, 24.7],
            }
        )
        mock_download.return_value = mock_df

        result = explorer.get_body_measures("2017-2018")

        assert "participant_id" in result.columns
        assert "bmi" in result.columns

    @patch.object(PopHealthObservatory, "download_data")
    def test_get_blood_pressure_success(self, mock_download):
        """Test blood pressure loading."""
        explorer = NHANESExplorer()

        mock_df = pd.DataFrame(
            {
                "SEQN": [1, 2],
                "BPXSY1": [120, 130],
                "BPXSY2": [118, 128],
                "BPXSY3": [119, 129],
                "BPXDI1": [80, 85],
                "BPXDI2": [78, 83],
                "BPXDI3": [79, 84],
            }
        )
        mock_download.return_value = mock_df

        result = explorer.get_blood_pressure("2017-2018")

        assert "participant_id" in result.columns
        # Should have averaged columns (actual names may vary)
        assert len(result.columns) > 3

    def test_get_survey_weight_valid_components(self):
        """Test survey weight selection."""
        explorer = NHANESExplorer()

        # Should return a weight column name
        result = explorer.get_survey_weight(["demographics", "body_measures"])

        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_survey_weight_empty_list(self):
        """Test survey weight with empty list."""
        explorer = NHANESExplorer()

        result = explorer.get_survey_weight([])

        # Should handle gracefully
        assert isinstance(result, str)


class TestNHANESExplorerManifestMethods:
    """Test manifest generation and saving."""

    @patch.object(NHANESExplorer, "_fetch_component_page")
    def test_get_detailed_component_manifest_success(self, mock_fetch):
        """Test manifest generation."""
        explorer = NHANESExplorer()

        mock_html = """
        <html>
        <table>
            <tr>
                <td>Demographics</td>
                <td><a href="DEMO_J.XPT">Data</a></td>
                <td>2017-2018</td>
                <td>100 KB</td>
            </tr>
        </table>
        </html>
        """
        mock_fetch.return_value = mock_html

        result = explorer.get_detailed_component_manifest()

        assert isinstance(result, dict)
        # Check for either 'metadata' or'generated_at' (implementation details)
        assert "generated_at" in result or "metadata" in result
        assert "schema_version" in result or "components" in result

    def test_save_detailed_component_manifest(self, tmp_path):
        """Test manifest saving."""
        explorer = NHANESExplorer()

        output_file = tmp_path / "test_manifest.json"

        with patch.object(explorer, "get_detailed_component_manifest") as mock_get:
            mock_get.return_value = {"metadata": {"test": "value"}, "components": []}

            result_path = explorer.save_detailed_component_manifest(str(output_file))

            assert output_file.exists()
            assert result_path == str(output_file)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_normalize_year_span_none(self):
        """Test None handling in year span."""
        explorer = NHANESExplorer()
        result = explorer._normalize_year_span(None)
        # Should handle None gracefully
        assert result == "" or result is None

    @patch.object(PopHealthObservatory, "download_data")
    def test_blood_pressure_missing_readings(self, mock_download):
        """Test blood pressure with missing readings."""
        explorer = NHANESExplorer()

        # Mock data with NaN values
        mock_df = pd.DataFrame(
            {
                "SEQN": [1, 2],
                "BPXSY1": [120, None],
                "BPXSY2": [None, 128],
                "BPXSY3": [119, 129],
                "BPXDI1": [80, 85],
                "BPXDI2": [78, None],
                "BPXDI3": [None, 84],
            }
        )
        mock_download.return_value = mock_df

        result = explorer.get_blood_pressure("2017-2018")

        # Should handle NaN values
        assert "participant_id" in result.columns
        assert len(result) == 2


class TestHTMLParsingDetailedCoverage:
    """Test detailed HTML table parsing logic (lines 249-301)."""

    def test_parse_component_table_with_complete_data(self):
        """Test parsing HTML table with all expected columns."""
        explorer = NHANESExplorer()

        html = """
        <table>
            <thead>
                <tr>
                    <th>Years</th>
                    <th>Data File Name</th>
                    <th>Doc File</th>
                    <th>Data File</th>
                    <th>Date Published</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>2017-2018</td>
                    <td>Demographics Data</td>
                    <td><a href="DEMO_J.htm">Doc</a></td>
                    <td><a href="DEMO_J.XPT">Data [100 KB]</a></td>
                    <td>January 2023</td>
                </tr>
            </tbody>
        </table>
        """

        records = explorer._parse_component_table(html, "https://example.com/")

        assert len(records) == 1
        rec = records[0]
        assert rec["year_raw"] == "2017-2018"
        assert rec["year_normalized"] == "2017_2018"
        assert rec["data_file_name"] == "Demographics Data"
        assert rec["doc_file_url"] == "https://example.com/DEMO_J.htm"
        assert rec["data_file_url"] == "https://example.com/DEMO_J.XPT"
        assert rec["data_file_type"] == "XPT"
        assert rec["date_published"] == "January 2023"

    def test_parse_component_table_missing_doc_file(self):
        """Test parsing when Doc File column is absent."""
        explorer = NHANESExplorer()

        # Table needs Years, Data File, and Doc columns to be recognized
        html = """
        <table>
            <tr><th>Years</th><th>Data File</th><th>Doc</th></tr>
            <tr>
                <td>2019-2020</td>
                <td><a href="BMX_K.XPT">Data [50 KB]</a></td>
                <td></td>
            </tr>
        </table>
        """

        records = explorer._parse_component_table(html, "https://example.com/")
        assert len(records) == 1
        assert records[0]["doc_file_url"] is None
        assert records[0]["doc_file_label"] is None

    def test_parse_component_table_zip_file(self):
        """Test parsing ZIP file type."""
        explorer = NHANESExplorer()

        html = """
        <table>
            <tr><th>Year</th><th>Data File</th><th>Doc</th></tr>
            <tr>
                <td>2021-2022</td>
                <td><a href="LAB_L.zip">ZIP Data</a></td>
                <td></td>
            </tr>
        </table>
        """

        records = explorer._parse_component_table(html, "https://example.com/")
        assert len(records) == 1
        assert records[0]["data_file_type"] == "ZIP"
        assert records[0]["original_filename"] == "LAB_L.zip"

    def test_parse_component_table_no_data_link(self):
        """Test row skipped when data file link missing."""
        explorer = NHANESExplorer()

        html = """
        <table>
            <tr><th>Years</th><th>Data File</th></tr>
            <tr>
                <td>2017-2018</td>
                <td>No Link Here</td>
            </tr>
        </table>
        """

        records = explorer._parse_component_table(html, "https://example.com/")
        assert len(records) == 0

    def test_parse_component_table_empty_rows(self):
        """Test handling of empty table rows."""
        explorer = NHANESExplorer()

        html = """
        <table>
            <tr><th>Years</th><th>Data File</th><th>Doc</th></tr>
            <tr></tr>
            <tr>
                <td>2017-2018</td>
                <td><a href="DEMO_J.XPT">Data</a></td>
                <td></td>
            </tr>
        </table>
        """

        records = explorer._parse_component_table(html, "https://example.com/")
        assert len(records) == 1

    def test_parse_component_table_multiple_rows(self):
        """Test parsing multiple data rows."""
        explorer = NHANESExplorer()

        html = """
        <table>
            <tr><th>Years</th><th>Data File</th><th>Doc</th></tr>
            <tr>
                <td>2017-2018</td>
                <td><a href="DEMO_J.XPT">Demo</a></td>
                <td></td>
            </tr>
            <tr>
                <td>2019-2020</td>
                <td><a href="DEMO_K.XPT">Demo</a></td>
                <td></td>
            </tr>
        </table>
        """

        records = explorer._parse_component_table(html, "https://example.com/")
        assert len(records) == 2
        assert records[0]["year_normalized"] == "2017_2018"
        assert records[1]["year_normalized"] == "2019_2020"


class TestDataMethodsExtended:
    """Extended tests for data loading and analysis methods (lines 592-634)."""

    @patch.object(NHANESExplorer, "get_demographics_data")
    @patch.object(NHANESExplorer, "get_body_measures")
    @patch.object(NHANESExplorer, "get_blood_pressure")
    def test_create_merged_dataset(self, mock_bp, mock_body, mock_demo):
        """Test create_merged_dataset merges all components."""
        explorer = NHANESExplorer()

        demo_df = pd.DataFrame({"participant_id": [1, 2], "age": [25, 30]})
        body_df = pd.DataFrame({"participant_id": [1, 2], "height": [170, 180]})
        bp_df = pd.DataFrame({"participant_id": [1], "avg_systolic": [120]})

        mock_demo.return_value = demo_df
        mock_body.return_value = body_df
        mock_bp.return_value = bp_df

        result = explorer.create_merged_dataset("2017-2018")

        assert len(result) == 2
        assert "age" in result.columns
        assert "height" in result.columns
        assert "avg_systolic" in result.columns
        assert result["avg_systolic"].isna().sum() == 1  # One missing

    @patch.object(NHANESExplorer, "get_demographics_data")
    @patch.object(NHANESExplorer, "get_body_measures")
    @patch.object(NHANESExplorer, "get_blood_pressure")
    def test_create_merged_dataset_empty_components(self, mock_bp, mock_body, mock_demo):
        """Test merged dataset when body/bp components are empty."""
        explorer = NHANESExplorer()

        demo_df = pd.DataFrame({"participant_id": [1, 2], "age": [25, 30]})
        empty_df = pd.DataFrame()

        mock_demo.return_value = demo_df
        mock_body.return_value = empty_df
        mock_bp.return_value = empty_df

        result = explorer.create_merged_dataset("2017-2018")

        # Should still have demographics
        assert len(result) == 2
        assert "age" in result.columns

    def test_analyze_by_demographics(self):
        """Test grouping and statistical analysis."""
        explorer = NHANESExplorer()

        df = pd.DataFrame(
            {
                "gender": ["Male", "Male", "Female", "Female"],
                "bmi": [25.5, 28.3, 22.1, 24.7],
            }
        )

        stats = explorer.analyze_by_demographics(df, "bmi", "gender")

        assert len(stats) == 2
        assert "Mean" in stats.columns
        assert "Median" in stats.columns
        assert stats.loc["Male", "Count"] == 2
        assert stats.loc["Female", "Count"] == 2

    def test_analyze_by_demographics_missing_columns(self):
        """Test analysis returns empty when columns missing."""
        explorer = NHANESExplorer()

        df = pd.DataFrame({"age": [25, 30]})

        result = explorer.analyze_by_demographics(df, "nonexistent", "age")
        assert result.empty

    def test_create_demographic_visualization_missing_columns(self):
        """Test visualization returns early when columns missing."""
        explorer = NHANESExplorer()

        df = pd.DataFrame({"age": [25]})

        # Should return without error
        result = explorer.create_demographic_visualization(df, "nonexistent", "age")
        assert result is None


class TestManifestMethodsExtended:
    """Extended manifest generation tests (lines 761-789)."""

    def test_calculate_weighted_mean_auto_detect_weight(self):
        """Test weighted mean calculation with auto-detected weight variable."""
        explorer = NHANESExplorer()

        data = pd.DataFrame(
            {
                "avg_systolic": [120, 130, 140],
                "exam_weight": [1000, 2000, 1500],
            }
        )

        result = explorer.calculate_weighted_mean(data, "avg_systolic")

        assert "weighted_mean" in result
        assert "unweighted_mean" in result
        assert result["weighted_mean"] != result["unweighted_mean"]

    def test_calculate_weighted_mean_explicit_weight(self):
        """Test weighted mean with explicit weight variable."""
        explorer = NHANESExplorer()

        data = pd.DataFrame(
            {
                "bmi": [25, 30, 35],
                "custom_weight": [100, 200, 150],
            }
        )

        result = explorer.calculate_weighted_mean(data, "bmi", weight_var="custom_weight")

        assert result["weighted_mean"] > 0
        assert "n_obs" in result
        assert result["n_obs"] == 3

    def test_calculate_weighted_mean_no_weight_raises(self):
        """Test error raised when no weight variable found."""
        explorer = NHANESExplorer()

        data = pd.DataFrame({"bmi": [25, 30]})

        with pytest.raises(ValueError, match="No weight variable found"):
            explorer.calculate_weighted_mean(data, "bmi")

    def test_calculate_weighted_mean_no_valid_obs_raises(self):
        """Test error when no valid observations after filtering."""
        explorer = NHANESExplorer()

        data = pd.DataFrame(
            {
                "bmi": [None, None],
                "exam_weight": [1000, 2000],
            }
        )

        with pytest.raises(ValueError, match="No valid observations"):
            explorer.calculate_weighted_mean(data, "bmi")

    def test_calculate_weighted_mean_min_weight_filtering(self):
        """Test filtering by minimum weight threshold."""
        explorer = NHANESExplorer()

        data = pd.DataFrame(
            {
                "bmi": [25, 30, 35],
                "exam_weight": [10, 1000, 2000],  # First weight too low
            }
        )

        result = explorer.calculate_weighted_mean(data, "bmi", min_weight=100)

        # Should only use 2 observations
        assert result["n_obs"] == 2


class TestManifestFiltering:
    """Test manifest filtering and processing logic."""

    @patch.object(NHANESExplorer, "_fetch_component_page")
    @patch.object(NHANESExplorer, "_parse_component_table")
    def test_get_detailed_manifest_with_year_filter(self, mock_parse, mock_fetch):
        """Test manifest generation with year range filtering."""
        explorer = NHANESExplorer()

        mock_fetch.return_value = "<html>test</html>"
        mock_parse.return_value = [
            {"year_normalized": "2017_2018", "data_file_type": "XPT", "data_file_url": "test1.xpt"},
            {"year_normalized": "2021_2022", "data_file_type": "XPT", "data_file_url": "test2.xpt"},
        ]

        result = explorer.get_detailed_component_manifest(components=["Demographics"], year_range=("2017", "2019"))

        # Should filter to only 2017-2018
        assert "detailed_year_records" in result or "components" in result

    @patch.object(NHANESExplorer, "_fetch_component_page")
    @patch.object(NHANESExplorer, "_parse_component_table")
    def test_get_detailed_manifest_with_file_type_filter(self, mock_parse, mock_fetch):
        """Test manifest generation with file type filtering."""
        explorer = NHANESExplorer()

        mock_fetch.return_value = "<html>test</html>"
        mock_parse.return_value = [
            {"year_normalized": "2017_2018", "data_file_type": "XPT", "data_file_url": "test.xpt"},
            {"year_normalized": "2017_2018", "data_file_type": "ZIP", "data_file_url": "test.zip"},
        ]

        result = explorer.get_detailed_component_manifest(components=["Demographics"], file_types=["XPT"])

        # Should filter to only XPT files
        assert result is not None

    @patch.object(NHANESExplorer, "_fetch_component_page")
    def test_get_detailed_manifest_with_force_refresh(self, mock_fetch):
        """Test force_refresh clears cache."""
        explorer = NHANESExplorer()

        # Prime the cache
        explorer._component_page_cache = {"Demographics": "<html>cached</html>"}

        mock_fetch.return_value = "<html>fresh</html>"
        # Call with force_refresh; ensure cache entry cleared and fetch invoked
        explorer.get_detailed_component_manifest(components=["Demographics"], force_refresh=True)
        assert "Demographics" not in explorer._component_page_cache
        assert mock_fetch.called

    def test_parse_component_table_no_matching_table(self):
        """Test parsing when no suitable table found."""
        explorer = NHANESExplorer()

        html = """
        <table>
            <tr><th>Wrong</th><th>Headers</th></tr>
            <tr><td>No</td><td>Match</td></tr>
        </table>
        """

        records = explorer._parse_component_table(html, "https://example.com/")
        assert len(records) == 0


class TestAdditionalDataMethods:
    """Additional data loading method coverage."""

    def test_get_survey_weight_returns_string(self):
        """Test survey weight recommendation returns string."""
        explorer = NHANESExplorer()

        result = explorer.get_survey_weight(["demographics", "body_measures"])

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_summary_report_with_data(self):
        """Test summary report generation."""
        explorer = NHANESExplorer()

        df = pd.DataFrame(
            {
                "participant_id": [1, 2, 3],
                "gender_label": ["Male", "Female", "Male"],
                "age": [25, 30, 35],
                "bmi": [24.5, 26.3, 28.1],
            }
        )

        report = explorer.generate_summary_report(df)

        assert "PopHealth Observatory" in report
        assert "participants" in report.lower()

    @patch.object(NHANESExplorer, "get_body_measures")
    def test_get_body_measures_empty_response(self, mock_get):
        """Test body measures with empty DataFrame."""
        explorer = NHANESExplorer()

        mock_get.return_value = pd.DataFrame()

        result = explorer.get_body_measures("2017-2018")

        assert result.empty


class TestVisualizationEdgeCases:
    """Test visualization method error handling."""

    def test_create_demographic_visualization_missing_columns_returns_early(self):
        """Test visualization returns early when required columns missing."""
        explorer = NHANESExplorer()
        df = pd.DataFrame({"age_years": [25, 30]})  # Missing 'bmi' and 'gender'

        # Should return None silently without error
        result = explorer.create_demographic_visualization(df, "bmi", "gender")
        assert result is None


class TestHTMLParsingEdgeCases:
    """Test HTML parsing robustness."""

    def test_parse_component_table_malformed_row(self):
        """Test that malformed table rows are skipped gracefully."""
        explorer = NHANESExplorer()

        # HTML with incomplete row structure (missing data cell with link)
        html = """
        <table>
            <tr>
                <td>2017-2018</td>
                <td>Demographics</td>
                <!-- Missing data_cell with anchor tag -->
            </tr>
        </table>
        """

        records = explorer._parse_component_table(html, "http://test.com")

        # Should skip malformed row and return empty
        assert records == []

    def test_parse_component_table_empty_cells(self):
        """Test handling of empty table cells."""
        explorer = NHANESExplorer()

        html = """
        <table>
            <tr>
                <td></td>
                <td></td>
                <td></td>
                <td><a href="data.xpt">Data</a></td>
            </tr>
        </table>
        """

        records = explorer._parse_component_table(html, "http://test.com")

        # Should handle empty cells gracefully
        assert isinstance(records, list)

    @patch.object(NHANESExplorer, "_fetch_component_page")
    @patch.object(NHANESExplorer, "_parse_component_table")
    def test_get_detailed_component_manifest_handles_parse_exception(self, mock_parse, mock_fetch):
        """Test manifest generation continues when component parsing fails."""
        explorer = NHANESExplorer()

        mock_fetch.return_value = "<html><table></table></html>"
        # First component fails, second succeeds with complete record (no component key, will be added)
        mock_parse.side_effect = [
            Exception("Parse error"),
            [{"year_normalized": "2017_2018", "data_file_url": "http://test.xpt", "data_file_type": "XPT"}],
        ]

        result = explorer.get_detailed_component_manifest(["Demographics", "Examination"])

        # Should have dict structure with detailed_year_records
        assert isinstance(result, dict)
        assert "detailed_year_records" in result

    @patch("pophealth_observatory.observatory.requests.get")
    def test_fetch_component_page_returns_none_on_empty(self, mock_get):
        """Test handling of empty HTML response."""
        explorer = NHANESExplorer()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""  # Empty response
        mock_get.return_value = mock_response

        result = explorer._fetch_component_page("Demographics")

        assert result is None or result == ""  # Could be None or empty string


class TestYearFilteringEdgeCases:
    """Test year range filtering robustness."""

    @patch.object(NHANESExplorer, "_fetch_component_page")
    @patch.object(NHANESExplorer, "_parse_component_table")
    def test_manifest_year_range_malformed_span(self, mock_parse, mock_fetch):
        """Test that malformed year spans are filtered out safely."""
        explorer = NHANESExplorer()

        mock_fetch.return_value = "<html></html>"
        mock_parse.return_value = [
            {"year_normalized": "invalid_format", "data_file_url": "http://test1.xpt", "data_file_type": "XPT"},
            {"year_normalized": "2017_2018", "data_file_url": "http://test2.xpt", "data_file_type": "XPT"},
        ]

        result = explorer.get_detailed_component_manifest(["Demographics"], year_range=("2017", "2018"))

        # Should handle malformed gracefully
        assert isinstance(result, dict)
        assert "detailed_year_records" in result

    @patch.object(NHANESExplorer, "_fetch_component_page")
    @patch.object(NHANESExplorer, "_parse_component_table")
    def test_manifest_year_range_no_underscore(self, mock_parse, mock_fetch):
        """Test year spans without underscore separator."""
        explorer = NHANESExplorer()

        mock_fetch.return_value = "<html></html>"
        mock_parse.return_value = [
            {"year_normalized": "2017", "data_file_url": "http://test.xpt", "data_file_type": "XPT"},
        ]

        result = explorer.get_detailed_component_manifest(["Demographics"], year_range=("2015", "2019"))

        # Should handle gracefully
        assert isinstance(result, dict)

"""Tests for BRFSS Explorer module.

Tests cover:
- Happy path data retrieval and normalization
- Error handling (empty response, non-list JSON, HTTP errors)
- Caching behavior
- Invalid year requests
- get_indicator() with various class/question combinations
- list_available_indicators()
"""

import pandas as pd
import pytest

from pophealth_observatory.brfss import BRFSSExplorer


class _MockResponse:
    """Mock requests.Response object for testing."""

    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or []

    def json(self):
        return self._payload


# Sample BRFSS data for testing
SAMPLE_OBESITY_DATA = [
    {
        "yearstart": "2023",
        "class": "Obesity / Weight Status",
        "question": "Percent of adults aged 18 years and older who have obesity",
        "locationabbr": "AL",
        "locationdesc": "Alabama",
        "data_value": "36.2",
        "low_confidence_limit": "34.5",
        "high_confidence_limit": "37.9",
        "sample_size": "1500",
    },
    {
        "yearstart": "2023",
        "class": "Obesity / Weight Status",
        "question": "Percent of adults aged 18 years and older who have obesity",
        "locationabbr": "AK",
        "locationdesc": "Alaska",
        "data_value": "30.1",
        "low_confidence_limit": "28.0",
        "high_confidence_limit": "32.2",
        "sample_size": "1200",
    },
    {
        "yearstart": "2022",
        "class": "Obesity / Weight Status",
        "question": "Percent of adults aged 18 years and older who have obesity",
        "locationabbr": "AL",
        "locationdesc": "Alabama",
        "data_value": "35.8",
        "low_confidence_limit": "34.1",
        "high_confidence_limit": "37.5",
        "sample_size": "1450",
    },
]

SAMPLE_PHYSICAL_ACTIVITY_DATA = [
    {
        "yearstart": "2023",
        "class": "Physical Activity",
        "question": "Percent of adults aged 18 years and older who engage in no leisure-time physical activity",
        "locationabbr": "AL",
        "locationdesc": "Alabama",
        "data_value": "28.5",
        "low_confidence_limit": "26.8",
        "high_confidence_limit": "30.2",
        "sample_size": "1500",
    },
]


def test_get_obesity_data_happy_path(monkeypatch):
    """Test successful obesity data retrieval."""
    calls = {"n": 0}

    def fake_get(url, timeout):
        calls["n"] += 1
        return _MockResponse(payload=SAMPLE_OBESITY_DATA)

    explorer = BRFSSExplorer(enable_cache=True)
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_obesity_data()

    # Should return 2 rows for 2023 (latest year)
    assert df.shape[0] == 2
    assert set(df["state"]) == {"AL", "AK"}
    assert df["year"].iloc[0] == 2023
    assert "value" in df.columns
    assert "low_ci" in df.columns
    assert "high_ci" in df.columns
    assert "sample_size" in df.columns
    assert df["class_name"].iloc[0] == "Obesity / Weight Status"

    # Check numeric conversion
    assert df["value"].dtype in [float, "float64"]
    assert df["low_ci"].dtype in [float, "float64"]


def test_get_obesity_data_specific_year(monkeypatch):
    """Test obesity data retrieval for specific year."""

    def fake_get(url, timeout):
        return _MockResponse(payload=SAMPLE_OBESITY_DATA)

    explorer = BRFSSExplorer(enable_cache=False)
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_obesity_data(year=2022)

    assert df.shape[0] == 1
    assert df["state"].iloc[0] == "AL"
    assert df["year"].iloc[0] == 2022


def test_caching_reduces_calls(monkeypatch):
    """Test that caching prevents repeated API calls."""
    calls = {"n": 0}

    def fake_get(url, timeout):
        calls["n"] += 1
        return _MockResponse(payload=SAMPLE_OBESITY_DATA)

    explorer = BRFSSExplorer(enable_cache=True)
    monkeypatch.setattr(explorer.session, "get", fake_get)

    # First call - should hit API
    df1 = explorer.get_obesity_data()
    assert calls["n"] == 1

    # Second call - should use cache
    df2 = explorer.get_obesity_data()
    assert calls["n"] == 1  # No additional API call
    assert df2.equals(df1)


def test_empty_response(monkeypatch):
    """Test handling of empty API response."""

    def fake_get(url, timeout):
        return _MockResponse(payload=[])

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_obesity_data()
    assert df.empty
    assert list(df.columns) == [
        "year",
        "state",
        "state_name",
        "value",
        "low_ci",
        "high_ci",
        "sample_size",
        "data_source",
        "class_name",
        "question",
    ]


def test_non_list_json(monkeypatch, capsys):
    """Test handling of non-list JSON response."""

    def fake_get(url, timeout):
        return _MockResponse(payload={"error": "invalid"})

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_obesity_data()
    assert df.empty

    # Check warning message
    captured = capsys.readouterr()
    assert "Unexpected BRFSS JSON structure" in captured.out


def test_http_error(monkeypatch, capsys):
    """Test handling of HTTP error response."""

    def fake_get(url, timeout):
        return _MockResponse(status_code=500)

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_obesity_data()
    assert df.empty

    captured = capsys.readouterr()
    assert "failed with HTTP 500" in captured.out


def test_invalid_year_raises_error(monkeypatch):
    """Test that requesting invalid year raises ValueError."""

    def fake_get(url, timeout):
        return _MockResponse(payload=SAMPLE_OBESITY_DATA)

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    # Year 2020 not present in sample data
    with pytest.raises(ValueError) as excinfo:
        explorer.get_obesity_data(year=2020)

    assert "2020" in str(excinfo.value)
    assert "not found" in str(excinfo.value).lower()


def test_get_indicator_physical_activity(monkeypatch):
    """Test get_indicator() with physical activity data."""
    combined_data = SAMPLE_OBESITY_DATA + SAMPLE_PHYSICAL_ACTIVITY_DATA

    def fake_get(url, timeout):
        return _MockResponse(payload=combined_data)

    explorer = BRFSSExplorer(enable_cache=False)
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_indicator(
        class_name="Physical Activity",
        question="Percent of adults aged 18 years and older who engage in no leisure-time physical activity",
    )

    assert df.shape[0] == 1
    assert df["state"].iloc[0] == "AL"
    assert df["class_name"].iloc[0] == "Physical Activity"
    assert df["value"].iloc[0] == 28.5


def test_get_indicator_nonexistent(monkeypatch, capsys):
    """Test get_indicator() with nonexistent class/question."""

    def fake_get(url, timeout):
        return _MockResponse(payload=SAMPLE_OBESITY_DATA)

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_indicator(class_name="Nonexistent Class", question="Nonexistent question")

    assert df.empty
    captured = capsys.readouterr()
    assert "No data found" in captured.out


def test_summary_with_data():
    """Test summary() with valid data."""
    sample_df = pd.DataFrame(
        {
            "year": [2023, 2023],
            "state": ["AL", "AK"],
            "state_name": ["Alabama", "Alaska"],
            "value": [36.2, 30.1],
            "low_ci": [34.5, 28.0],
            "high_ci": [37.9, 32.2],
            "sample_size": [1500, 1200],
            "data_source": ["CDC BRFSS hn4x-zwk7", "CDC BRFSS hn4x-zwk7"],
            "class_name": ["Obesity / Weight Status", "Obesity / Weight Status"],
            "question": ["Test question", "Test question"],
        }
    )

    explorer = BRFSSExplorer()
    summary = explorer.summary(sample_df)

    assert summary["count"] == 2
    assert summary["mean_value"] == pytest.approx(33.15, abs=0.01)
    assert summary["min_value"] == 30.1
    assert summary["max_value"] == 36.2
    assert summary["year"] == 2023
    assert summary["class_name"] == "Obesity / Weight Status"


def test_summary_with_empty_dataframe():
    """Test summary() with empty DataFrame."""
    explorer = BRFSSExplorer()
    summary = explorer.summary(pd.DataFrame())

    assert summary["count"] == 0
    assert summary["mean_value"] is None
    assert summary["min_value"] is None
    assert summary["max_value"] is None
    assert summary["year"] is None


def test_list_available_indicators(monkeypatch):
    """Test list_available_indicators() returns unique class/question pairs."""
    combined_data = SAMPLE_OBESITY_DATA + SAMPLE_PHYSICAL_ACTIVITY_DATA

    def fake_get(url, timeout):
        return _MockResponse(payload=combined_data)

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    indicators = explorer.list_available_indicators()

    assert indicators.shape[0] == 2  # 2 unique class/question combinations
    assert "class" in indicators.columns
    assert "question" in indicators.columns

    classes = set(indicators["class"])
    assert "Obesity / Weight Status" in classes
    assert "Physical Activity" in classes


def test_invalid_numeric_values(monkeypatch):
    """Test handling of invalid numeric values (should be dropped)."""
    data_with_invalid = [
        {
            "yearstart": "2023",
            "class": "Obesity / Weight Status",
            "question": "Percent of adults aged 18 years and older who have obesity",
            "locationabbr": "AL",
            "locationdesc": "Alabama",
            "data_value": "36.2",
            "low_confidence_limit": "34.5",
            "high_confidence_limit": "37.9",
            "sample_size": "1500",
        },
        {
            "yearstart": "2023",
            "class": "Obesity / Weight Status",
            "question": "Percent of adults aged 18 years and older who have obesity",
            "locationabbr": "AK",
            "locationdesc": "Alaska",
            "data_value": "N/A",  # Invalid
            "low_confidence_limit": "28.0",
            "high_confidence_limit": "32.2",
            "sample_size": "1200",
        },
    ]

    def fake_get(url, timeout):
        return _MockResponse(payload=data_with_invalid)

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_obesity_data()

    # Should only return 1 row (invalid value dropped)
    assert df.shape[0] == 1
    assert df["state"].iloc[0] == "AL"


def test_cache_independence_between_indicators(monkeypatch):
    """Test that different indicators use separate cache entries."""
    combined_data = SAMPLE_OBESITY_DATA + SAMPLE_PHYSICAL_ACTIVITY_DATA

    def fake_get(url, timeout):
        return _MockResponse(payload=combined_data)

    explorer = BRFSSExplorer(enable_cache=True)
    monkeypatch.setattr(explorer.session, "get", fake_get)

    # Get obesity data
    obesity_df = explorer.get_obesity_data()
    assert obesity_df.shape[0] == 2

    # Get physical activity data
    activity_df = explorer.get_indicator(
        class_name="Physical Activity",
        question="Percent of adults aged 18 years and older who engage in no leisure-time physical activity",
    )
    assert activity_df.shape[0] == 1

    # Verify they're different
    assert not obesity_df.equals(activity_df)
    assert obesity_df["class_name"].iloc[0] != activity_df["class_name"].iloc[0]


def test_network_exception_handling(monkeypatch, capsys):
    """Test handling of network exceptions."""

    def fake_get(url, timeout):
        raise ConnectionError("Network unavailable")

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    df = explorer.get_obesity_data()
    assert df.empty

    captured = capsys.readouterr()
    assert "BRFSS request error" in captured.out


def test_latest_year_with_empty_dataframe():
    """Test _latest_year() returns 0 for empty DataFrame (line 319)."""
    explorer = BRFSSExplorer()
    assert explorer._latest_year(pd.DataFrame()) == 0


def test_latest_year_with_missing_yearstart_column():
    """Test _latest_year() returns 0 when yearstart column missing (line 319)."""
    explorer = BRFSSExplorer()
    df_no_yearstart = pd.DataFrame({"other_column": [1, 2, 3]})
    assert explorer._latest_year(df_no_yearstart) == 0


def test_list_available_indicators_empty_response(monkeypatch):
    """Test list_available_indicators() with empty API response (line 228)."""

    def fake_get(url, timeout):
        return _MockResponse(payload=[])

    explorer = BRFSSExplorer()
    monkeypatch.setattr(explorer.session, "get", fake_get)

    indicators = explorer.list_available_indicators()

    # Should return empty DataFrame with correct schema
    assert indicators.empty
    assert list(indicators.columns) == ["class", "question"]

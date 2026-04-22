from unittest.mock import Mock, patch

from pophealth_observatory.nhanes_manifest_service import (
    build_detailed_component_manifest,
    classify_data_file,
    derive_local_filename,
    extract_size,
    normalize_year_span,
    parse_component_table,
)


def test_manifest_service_normalize_year_span_variants():
    assert normalize_year_span("2017-2018") == "2017_2018"
    assert normalize_year_span("2017\u20132018") == "2017_2018"
    assert normalize_year_span("2017 - 2018") == "2017_2018"
    assert normalize_year_span(None) == ""


def test_manifest_service_classify_and_size_helpers():
    assert classify_data_file("https://x/DEMO_J.XPT", "Data") == "XPT"
    assert classify_data_file("https://x/LAB.zip", "Data") == "ZIP"
    assert classify_data_file("ftp://x/LAB", "Data") == "FTP"
    assert classify_data_file("https://x/page", "Data") == "OTHER"
    assert extract_size("Data [3.4 MB]") == "3.4 MB"
    assert extract_size("No size token") is None


def test_manifest_service_derive_local_filename():
    assert derive_local_filename("https://x/DEMO_J.XPT", "2017_2018") == "DEMO_2017_2018.xpt"
    assert derive_local_filename("https://x/LAB.zip", "2017_2018") is None


def test_manifest_service_parse_component_table_complete_record():
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

    records = parse_component_table(html, "https://example.com/")
    assert len(records) == 1
    record = records[0]
    assert record["year_normalized"] == "2017_2018"
    assert record["data_file_type"] == "XPT"
    assert record["data_file_size"] == "100 KB"


def test_manifest_service_build_manifest_uses_callbacks_and_filters():
    cache = {"Demographics": "stale"}

    fetch_page = Mock(return_value="<html>ok</html>")
    parse_table = Mock(
        return_value=[
            {"year_normalized": "2017_2018", "data_file_type": "XPT", "data_file_url": "x"},
            {"year_normalized": "2021_2022", "data_file_type": "ZIP", "data_file_url": "y"},
        ]
    )

    manifest = build_detailed_component_manifest(
        components=["Demographics"],
        as_dataframe=True,
        year_range=("2017", "2019"),
        file_types=["XPT"],
        force_refresh=True,
        schema_version="1.0.0",
        cache=cache,
        fetch_page=fetch_page,
        parse_table=parse_table,
    )

    assert fetch_page.called
    assert parse_table.called
    assert "Demographics" not in cache
    assert manifest["component_count"] == 1
    assert manifest["total_file_rows"] == 1
    assert "dataframe" in manifest


@patch("pophealth_observatory.nhanes_manifest_service.requests.get")
@patch("pophealth_observatory.nhanes_manifest_service.time.sleep")
def test_manifest_service_fetch_page_cache_hit_skips_network(mock_sleep, mock_get):
    from pophealth_observatory.nhanes_manifest_service import fetch_component_page

    cache = {"Demographics": "cached"}
    html = fetch_component_page("Demographics", cache)
    assert html == "cached"
    mock_get.assert_not_called()
    mock_sleep.assert_not_called()

from unittest.mock import Mock, patch

import pandas as pd

from pophealth_observatory.nhanes_data_access import build_nhanes_xpt_url_patterns, try_download_xpt


def test_build_nhanes_xpt_url_patterns_contains_expected_variants():
    patterns = build_nhanes_xpt_url_patterns(
        cycle="2017-2018",
        component="DEMO",
        letter="J",
        base_url="https://wwwn.cdc.gov/Nchs/Nhanes",
        alt_base_url="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public",
    )

    assert len(patterns) >= 6
    assert patterns[0].endswith("/2017/DataFiles/DEMO_J.xpt")
    assert any("/2017-2018/DEMO_J.XPT" in p for p in patterns)
    assert any("/20172018/DEMO_18.XPT" in p for p in patterns)


@patch("pophealth_observatory.nhanes_data_access.pd.read_sas")
@patch("pophealth_observatory.nhanes_data_access.requests.get")
def test_try_download_xpt_returns_first_valid_dataframe(mock_get, mock_read_sas):
    missing_response = Mock(status_code=404, content=b"")
    ok_response = Mock(status_code=200, content=b"fake-xpt")
    mock_get.side_effect = [missing_response, ok_response]

    parsed_df = pd.DataFrame({"SEQN": [1, 2]})
    mock_read_sas.return_value = parsed_df

    df, success_url, errors = try_download_xpt(["https://a", "https://b"])

    assert success_url == "https://b"
    assert df is parsed_df
    assert len(errors) == 1
    assert "Status 404" in errors[0]


@patch("pophealth_observatory.nhanes_data_access.pd.read_sas")
@patch("pophealth_observatory.nhanes_data_access.requests.get")
def test_try_download_xpt_returns_none_when_all_fail(mock_get, mock_read_sas):
    ok_but_empty = Mock(status_code=200, content=b"empty-xpt")
    mock_get.return_value = ok_but_empty
    mock_read_sas.return_value = pd.DataFrame()

    df, success_url, errors = try_download_xpt(["https://a"])

    assert df is None
    assert success_url is None
    assert len(errors) == 1
    assert "Empty DataFrame" in errors[0]

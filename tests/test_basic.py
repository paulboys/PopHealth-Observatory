import pytest
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pophealth_observatory import NHANESExplorer


def test_instantiate():
    explorer = NHANESExplorer()
    assert 'demographics' in explorer.components
    assert isinstance(explorer.available_cycles, list)


def test_get_data_url_format():
    explorer = NHANESExplorer()
    url = explorer.get_data_url('2017-2018', explorer.components['demographics'])
    assert url.endswith('.XPT')
    assert 'DEMO' in url


def test_download_handles_bad_component(monkeypatch):
    explorer = NHANESExplorer()

    class FakeResp:
        def raise_for_status(self):
            raise Exception('boom')
    
    def fake_get(*args, **kwargs):
        return FakeResp()

    import pophealth_observatory.observatory as obs
    monkeypatch.setattr(obs.requests, 'get', fake_get)
    df = explorer.download_data('2017-2018', 'DEMO')
    # Should return empty DataFrame on failure
    assert df.empty


def test_summary_report_structure():
    explorer = NHANESExplorer()
    # minimal synthetic frame matching expected columns
    import pandas as pd
    df = pd.DataFrame({
        'age_years': [25, 40],
        'gender_label': ['Male', 'Female'],
        'race_ethnicity_label': ['Non-Hispanic White', 'Non-Hispanic Black'],
        'bmi': [22.0, 30.5],
        'avg_systolic': [118, 132],
        'avg_diastolic': [76, 84],
        'weight_kg': [70, 85],
        'height_cm': [175, 163]
    })
    report = explorer.generate_summary_report(df)
    assert 'Health Metrics Summary:' in report
    assert 'Total Participants' in report

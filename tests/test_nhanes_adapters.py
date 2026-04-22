from __future__ import annotations

import pandas as pd

from pophealth_observatory.core import AnalysisRunner, DataProvider, NHANESAnalysisAdapter, NHANESDataProviderAdapter
from pophealth_observatory.observatory import NHANESExplorer, PopHealthObservatory


class _StubProvider:
    def get_data_url(self, cycle: str, component: str) -> str:
        return f"https://example.test/{cycle}/{component}.XPT"

    def download_data(self, cycle: str, component: str) -> pd.DataFrame:
        if component == "DEMO":
            return pd.DataFrame({"SEQN": [1, 2], "RIAGENDR": [1, 2], "RIDAGEYR": [25, 30], "RIDRETH3": [3, 1]})
        if component == "BMX":
            return pd.DataFrame({"SEQN": [1, 2], "BMXBMI": [24.2, 31.0]})
        if component == "BPX":
            return pd.DataFrame(
                {
                    "SEQN": [1, 2],
                    "BPXSY1": [120, 145],
                    "BPXDI1": [80, 95],
                }
            )
        return pd.DataFrame()


def test_nhanes_data_provider_adapter_satisfies_protocol() -> None:
    backend = PopHealthObservatory()
    adapter = NHANESDataProviderAdapter(backend)
    assert isinstance(adapter, DataProvider)


def test_nhanes_analysis_adapter_satisfies_protocol() -> None:
    adapter = NHANESAnalysisAdapter(
        get_demographics_data=lambda cycle: pd.DataFrame({"participant_id": [1]}),
        get_body_measures=lambda cycle: pd.DataFrame({"participant_id": [1], "bmi": [25.0]}),
        get_blood_pressure=lambda cycle: pd.DataFrame({"participant_id": [1], "avg_systolic": [120.0]}),
        analyze_by_demographics=lambda df, metric, demographic: pd.DataFrame({"Count": [1]}, index=["x"]),
    )
    assert isinstance(adapter, AnalysisRunner)


def test_nhanes_explorer_uses_injected_data_provider() -> None:
    explorer = NHANESExplorer(data_provider=_StubProvider())

    demo = explorer.get_demographics_data("2017-2018")
    body = explorer.get_body_measures("2017-2018")
    bp = explorer.get_blood_pressure("2017-2018")
    merged = explorer.create_merged_dataset("2017-2018")

    assert "participant_id" in demo.columns
    assert "bmi" in body.columns
    assert "avg_systolic" in bp.columns
    assert "participant_id" in merged.columns

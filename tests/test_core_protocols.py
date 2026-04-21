"""Contract tests for core protocol interfaces."""

from __future__ import annotations

from pophealth_observatory.brfss import BRFSSExplorer
from pophealth_observatory.core import AnalysisRunner, DataProvider, IndicatorProvider, ReportGenerator
from pophealth_observatory.observatory import NHANESExplorer, PopHealthObservatory


def test_pophealth_observatory_satisfies_data_provider_protocol() -> None:
    provider = PopHealthObservatory()
    assert isinstance(provider, DataProvider)


def test_nhanes_explorer_satisfies_core_protocols() -> None:
    explorer = NHANESExplorer()
    assert isinstance(explorer, DataProvider)
    assert isinstance(explorer, AnalysisRunner)
    assert isinstance(explorer, ReportGenerator)


def test_brfss_explorer_satisfies_indicator_provider_protocol() -> None:
    explorer = BRFSSExplorer()
    assert isinstance(explorer, IndicatorProvider)


def test_brfss_explorer_does_not_claim_nhanes_report_contract() -> None:
    explorer = BRFSSExplorer()
    assert not isinstance(explorer, ReportGenerator)

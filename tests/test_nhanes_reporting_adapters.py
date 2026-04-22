from __future__ import annotations

from unittest.mock import Mock, patch

import pandas as pd

from pophealth_observatory.core import NHANESReportAdapter
from pophealth_observatory.core.nhanes_reporting_adapters import NHANESValidationAdapter
from pophealth_observatory.observatory import NHANESExplorer


def test_nhanes_report_adapter_delegates_summary_and_validate() -> None:
    adapter = NHANESReportAdapter(
        generate_summary_report=lambda df: "ok-summary",
        validate=lambda cycle, components: {"status": "PASS", "cycle": cycle, "components": components},
    )

    summary = adapter.generate_summary_report(pd.DataFrame({"x": [1]}))
    report = adapter.validate("2017-2018", ["demographics"])

    assert summary == "ok-summary"
    assert report["status"] == "PASS"
    assert report["cycle"] == "2017-2018"


@patch("pophealth_observatory.validation.run_validation")
def test_nhanes_validation_adapter_returns_dict_report(mock_run_validation: Mock) -> None:
    class _ExplorerStub:
        pass

    mock_report = Mock()
    mock_report.to_dict.return_value = {"cycle": "2017-2018", "status": "PASS", "components": {}}
    mock_run_validation.return_value = mock_report

    adapter = NHANESValidationAdapter(_ExplorerStub())
    result = adapter.validate("2017-2018", ["demographics"])

    assert result["status"] == "PASS"
    mock_run_validation.assert_called_once()
    mock_report.to_dict.assert_called_once()


def test_nhanes_explorer_uses_injected_report_generator() -> None:
    class _ReportGeneratorStub:
        def generate_summary_report(self, df: pd.DataFrame) -> str:
            return "stub-summary"

        def validate(self, cycle: str, components: list[str]):
            return {"cycle": cycle, "status": "WARN", "components": {}}

    explorer = NHANESExplorer(report_generator=_ReportGeneratorStub())

    summary = explorer.generate_summary_report(pd.DataFrame({"x": [1]}))
    validation = explorer.validate("2017-2018", ["demographics"])

    assert summary == "stub-summary"
    assert validation["status"] == "WARN"


def test_nhanes_explorer_default_report_paths_work() -> None:
    explorer = NHANESExplorer()
    summary = explorer.generate_summary_report(pd.DataFrame({"age_years": [25, 40]}))

    assert "PopHealth Observatory Summary Report" in summary

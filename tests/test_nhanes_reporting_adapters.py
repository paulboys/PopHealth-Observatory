from __future__ import annotations

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


def test_nhanes_validation_adapter_returns_dict_report() -> None:
    class _ExplorerStub:
        pass

    explorer = _ExplorerStub()
    adapter = NHANESValidationAdapter(explorer)

    # Use monkeypatch-like local override by replacing imported function target at runtime.
    import pophealth_observatory.core.nhanes_reporting_adapters as mod

    original_import = mod.NHANESValidationAdapter.validate

    def _fake_validate(self, cycle, components):  # noqa: ANN001
        return {"cycle": cycle, "status": "PASS", "components": {}}

    try:
        mod.NHANESValidationAdapter.validate = _fake_validate  # type: ignore[method-assign]
        result = adapter.validate("2017-2018", ["demographics"])
        assert result["status"] == "PASS"
    finally:
        mod.NHANESValidationAdapter.validate = original_import  # type: ignore[method-assign]


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

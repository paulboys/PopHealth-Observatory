"""Protocol-backed reporting and validation adapters for NHANES."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from .protocols import ReportGenerator


class NHANESReportAdapter(ReportGenerator):
    """Report adapter composed from summary and validation callables."""

    def __init__(
        self,
        generate_summary_report: Callable[[pd.DataFrame], str],
        validate: Callable[[str, list[str]], dict[str, Any]],
    ):
        self._generate_summary_report = generate_summary_report
        self._validate = validate

    def generate_summary_report(self, df: pd.DataFrame) -> str:
        return self._generate_summary_report(df)

    def validate(self, cycle: str, components: list[str]) -> dict[str, Any]:
        return self._validate(cycle, components)


class NHANESValidationAdapter:
    """Validation adapter wrapping the existing run_validation workflow."""

    def __init__(self, explorer: Any):
        self._explorer = explorer

    def validate(self, cycle: str, components: list[str]) -> dict[str, Any]:
        from ..validation import run_validation

        validation_report = run_validation(self._explorer, cycle, components)
        return validation_report.to_dict()

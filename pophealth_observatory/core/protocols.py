"""Core protocol contracts for explorer and reporting interfaces.

These protocols provide lightweight, structural contracts that guide future
refactoring toward interface-driven composition while preserving backward
compatibility with existing concrete classes.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataProvider(Protocol):
    """Contract for survey data providers with cycle/component retrieval."""

    def get_data_url(self, cycle: str, component: str) -> str:
        """Return a retrieval URL for a cycle/component pair."""

    def download_data(self, cycle: str, component: str) -> pd.DataFrame:
        """Download component data for a given cycle."""


@runtime_checkable
class AnalysisRunner(Protocol):
    """Contract for NHANES-style analysis workflows."""

    def create_merged_dataset(self, cycle: str = "2017-2018") -> pd.DataFrame:
        """Build a merged analysis dataset for a survey cycle."""

    def analyze_by_demographics(self, df: pd.DataFrame, metric: str, demographic: str) -> pd.DataFrame:
        """Aggregate a metric by demographic grouping."""


@runtime_checkable
class ReportGenerator(Protocol):
    """Contract for summary and validation reporting."""

    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """Generate a human-readable summary report from a DataFrame."""

    def validate(self, cycle: str, components: list[str]) -> dict[str, Any]:
        """Validate cycle/component data and return a structured report."""


@runtime_checkable
class IndicatorProvider(Protocol):
    """Contract for state/indicator datasets such as BRFSS."""

    def get_indicator(self, class_name: str, question: str, year: int | None = None) -> pd.DataFrame:
        """Fetch indicator values for a class/question and optional year."""

    def summary(self, df: pd.DataFrame) -> dict[str, Any]:
        """Return summary statistics for an indicator DataFrame."""

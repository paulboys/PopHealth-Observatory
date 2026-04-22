"""Protocol-backed NHANES adapter implementations."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pandas as pd

from ..logging_config import log_with_fallback
from .protocols import AnalysisRunner, DataProvider

logger = logging.getLogger(__name__)


class NHANESDataProviderAdapter(DataProvider):
    """Data provider adapter delegating to an existing observatory backend."""

    def __init__(self, backend: DataProvider):
        self._backend = backend

    def get_data_url(self, cycle: str, component: str) -> str:
        return self._backend.get_data_url(cycle, component)

    def download_data(self, cycle: str, component: str) -> pd.DataFrame:
        return self._backend.download_data(cycle, component)


class NHANESAnalysisAdapter(AnalysisRunner):
    """Analysis runner adapter composed from NHANES explorer callables."""

    def __init__(
        self,
        get_demographics_data: Callable[[str], pd.DataFrame],
        get_body_measures: Callable[[str], pd.DataFrame],
        get_blood_pressure: Callable[[str], pd.DataFrame],
        analyze_by_demographics: Callable[[pd.DataFrame, str, str], pd.DataFrame],
    ):
        self._get_demographics_data = get_demographics_data
        self._get_body_measures = get_body_measures
        self._get_blood_pressure = get_blood_pressure
        self._analyze_by_demographics = analyze_by_demographics

    def create_merged_dataset(self, cycle: str = "2017-2018") -> pd.DataFrame:
        log_with_fallback(logger, logging.INFO, f"Creating merged dataset for {cycle}...")
        demo_df = self._get_demographics_data(cycle)
        body_df = self._get_body_measures(cycle)
        bp_df = self._get_blood_pressure(cycle)

        merged = demo_df.copy()
        if not body_df.empty:
            merged = merged.merge(body_df, on="participant_id", how="left")
        if not bp_df.empty:
            merged = merged.merge(bp_df, on="participant_id", how="left")

        log_with_fallback(
            logger,
            logging.INFO,
            f"Merged dataset created with {len(merged)} participants and {len(merged.columns)} variables",
        )
        return merged

    def analyze_by_demographics(self, df: pd.DataFrame, metric: str, demographic: str) -> pd.DataFrame:
        return self._analyze_by_demographics(df, metric, demographic)

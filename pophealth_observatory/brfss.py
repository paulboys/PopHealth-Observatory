"""
BRFSS (Behavioral Risk Factor Surveillance System) data access.

This module provides the BRFSSExplorer class for retrieving state-level health
indicators from the CDC BRFSS Nutrition, Physical Activity, and Obesity dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests


@dataclass
class BRFSSConfig:
    """Configuration for BRFSS API access.

    Attributes
    ----------
    base_url : str
        CDC BRFSS API endpoint (dataset hn4x-zwk7).
    timeout : int
        HTTP request timeout in seconds.
    default_limit : int
        Default API result limit (5000 captures all current records).
    """

    base_url: str = "https://data.cdc.gov/resource/hn4x-zwk7.json"
    timeout: int = 30
    default_limit: int = 5000


class BRFSSExplorer:
    """
    Explorer for CDC BRFSS state-level health indicators.

    Provides access to obesity prevalence and other health metrics from the
    Behavioral Risk Factor Surveillance System (BRFSS) dataset. Complements
    NHANES national-level data with state-level geographic estimates.

    Parameters
    ----------
    config : BRFSSConfig, optional
        Configuration object with base URL, timeout, and default limit.
    session : requests.Session, optional
        Reusable HTTP session (enables connection pooling).
    enable_cache : bool, default True
        Whether to cache normalized DataFrames in-memory.

    Examples
    --------
    >>> brfss = BRFSSExplorer()
    >>> obesity_df = brfss.get_obesity_data()
    >>> print(brfss.summary(obesity_df))

    >>> # Get specific indicator
    >>> diabetes_df = brfss.get_indicator(
    ...     class_name='Diabetes',
    ...     question='Percent of adults aged 18 years and older who have been told they have diabetes'
    ... )

    Notes
    -----
    - All numeric conversions are coercive: invalid values become NaN and are dropped.
    - Cache is keyed by indicator type and year for efficient repeated access.
    - Network failures return empty DataFrames with printed warnings (no exceptions).
    """

    def __init__(
        self,
        config: BRFSSConfig | None = None,
        session: requests.Session | None = None,
        enable_cache: bool = True,
    ) -> None:
        self.config = config or BRFSSConfig()
        self.session = session or requests.Session()
        self._cache: dict[str, pd.DataFrame] = {}
        self.enable_cache = enable_cache
        self._raw_cache: pd.DataFrame | None = None

    # --------------- Public API -----------------

    def get_obesity_data(self, year: int | None = None) -> pd.DataFrame:
        """
        Retrieve normalized state-level adult obesity prevalence.

        Fetches data for the standard BRFSS obesity question:
        "Percent of adults aged 18 years and older who have obesity"

        Parameters
        ----------
        year : int, optional
            Target year. If None, automatically detects latest year available.

        Returns
        -------
        DataFrame
            Columns: year, state, state_name, value, low_ci, high_ci,
            sample_size, data_source, class_name, question.
            Returns empty DataFrame if no data found.

        Raises
        ------
        ValueError
            If year is provided but not present in raw dataset.

        Examples
        --------
        >>> brfss = BRFSSExplorer()
        >>> obesity_df = brfss.get_obesity_data(year=2022)
        >>> print(f"States: {obesity_df.shape[0]}")
        """
        return self.get_indicator(
            class_name="Obesity / Weight Status",
            question="Percent of adults aged 18 years and older who have obesity",
            year=year,
        )

    def get_indicator(self, class_name: str, question: str, year: int | None = None) -> pd.DataFrame:
        """
        Retrieve normalized state-level data for any BRFSS indicator.

        Generic method for fetching any health metric available in the BRFSS
        dataset by specifying its class and question text.

        Parameters
        ----------
        class_name : str
            BRFSS indicator class (e.g., 'Obesity / Weight Status', 'Physical Activity').
            Must match exact class name in dataset.
        question : str
            Full question text as it appears in BRFSS dataset.
            Must match exactly (case-sensitive).
        year : int, optional
            Target year. If None, automatically detects latest year available
            for this specific indicator.

        Returns
        -------
        DataFrame
            Normalized data with columns: year, state, state_name, value, low_ci,
            high_ci, sample_size, data_source, class_name, question.
            Returns empty DataFrame if no matching data found.

        Raises
        ------
        ValueError
            If year is provided but not present in dataset for this indicator.

        Examples
        --------
        >>> brfss = BRFSSExplorer()
        >>> physical_inactivity = brfss.get_indicator(
        ...     class_name='Physical Activity',
        ...     question='Percent of adults aged 18 years and older who engage in no leisure-time physical activity'
        ... )
        >>> print(physical_inactivity.head())

        Notes
        -----
        Use list_available_indicators() to discover valid class/question combinations.
        """
        # Generate cache key
        cache_key = f"{class_name}::{question}::{year or 'latest'}"
        if self.enable_cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # Fetch raw data
        raw = self._get_raw(limit=self.config.default_limit)
        if raw.empty:
            return self._empty_indicator_df()

        # Filter for this specific indicator
        indicator_rows = raw[(raw["class"] == class_name) & (raw["question"] == question)].copy()

        if indicator_rows.empty:
            print(f"⚠ No data found for class='{class_name}', question='{question}'")
            return self._empty_indicator_df()

        # Determine target year
        target_year = year or self._latest_year(indicator_rows)
        # Convert yearstart to int for comparison (stored as string in dataset)
        available_years = pd.to_numeric(indicator_rows["yearstart"], errors="coerce").dropna().astype(int).unique()
        if target_year not in available_years:
            raise ValueError(
                f"Year {target_year} not found for indicator '{question}' "
                f"in class '{class_name}'. Available years: "
                f"{sorted(available_years)}"
            )

        # Filter by year (convert to string for comparison with dataset)
        year_rows = indicator_rows[indicator_rows["yearstart"] == str(target_year)].copy()
        if year_rows.empty:
            return self._empty_indicator_df()

        # Normalize
        normalized = self._normalize(year_rows, class_name, question)
        if self.enable_cache:
            self._cache[cache_key] = normalized.copy()

        return normalized

    def list_available_indicators(self) -> pd.DataFrame:
        """
        List all unique class/question combinations available in BRFSS dataset.

        Useful for discovering what indicators can be fetched with get_indicator().

        Returns
        -------
        DataFrame
            Columns: class, question.
            Sorted by class then question for readability.
            Returns empty DataFrame if API request fails.

        Examples
        --------
        >>> brfss = BRFSSExplorer()
        >>> indicators = brfss.list_available_indicators()
        >>> print(f"Total indicators: {len(indicators)}")
        >>> print(indicators[indicators['class'] == 'Obesity / Weight Status'])
        """
        raw = self._get_raw(limit=self.config.default_limit)
        if raw.empty or "class" not in raw.columns or "question" not in raw.columns:
            return pd.DataFrame(columns=["class", "question"])

        indicators = (
            raw[["class", "question"]].drop_duplicates().sort_values(["class", "question"]).reset_index(drop=True)
        )
        return indicators

    def summary(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Produce summary statistics for an indicator DataFrame.

        Parameters
        ----------
        df : DataFrame
            Output of get_obesity_data() or get_indicator().

        Returns
        -------
        dict
            Keys: count, mean_value, min_value, max_value, year, class_name, question.
            Returns dict with None values if DataFrame is empty.

        Examples
        --------
        >>> brfss = BRFSSExplorer()
        >>> obesity_df = brfss.get_obesity_data()
        >>> stats = brfss.summary(obesity_df)
        >>> print(f"Mean obesity rate: {stats['mean_value']:.1f}%")
        """
        if df.empty:
            return {
                "count": 0,
                "mean_value": None,
                "min_value": None,
                "max_value": None,
                "year": None,
                "class_name": None,
                "question": None,
            }

        return {
            "count": int(df.shape[0]),
            "mean_value": round(float(df["value"].mean()), 2),
            "min_value": round(float(df["value"].min()), 2),
            "max_value": round(float(df["value"].max()), 2),
            "year": int(df["year"].iloc[0]) if "year" in df.columns else None,
            "class_name": str(df["class_name"].iloc[0]) if "class_name" in df.columns else None,
            "question": str(df["question"].iloc[0]) if "question" in df.columns else None,
        }

    # --------------- Internal Helpers -----------------

    def _build_url(self, limit: int) -> str:
        """Construct API URL with limit parameter."""
        return f"{self.config.base_url}?$limit={limit}"

    def _get_raw(self, limit: int) -> pd.DataFrame:
        """
        Fetch raw BRFSS data from CDC API.

        Uses cached raw data if available to avoid repeated network calls.
        """
        # Return cached raw data if available
        if self._raw_cache is not None:
            return self._raw_cache

        url = self._build_url(limit=limit)
        try:
            resp = self.session.get(url, timeout=self.config.timeout)
            if resp.status_code != 200:
                print(f"⚠ BRFSS request failed with HTTP {resp.status_code}")
                return pd.DataFrame()

            data = resp.json()
            if not isinstance(data, list):
                print("⚠ Unexpected BRFSS JSON structure (not a list).")
                return pd.DataFrame()

            df = pd.DataFrame(data)

            # Cache raw data for subsequent calls
            self._raw_cache = df

            return df
        except Exception as e:
            print(f"❌ BRFSS request error: {e}")
            return pd.DataFrame()

    def _latest_year(self, raw: pd.DataFrame) -> int:
        """Extract most recent year from yearstart column."""
        if raw.empty or "yearstart" not in raw.columns:
            return 0
        # yearstart is stored as string sometimes
        years = pd.to_numeric(raw["yearstart"], errors="coerce").dropna().astype(int)
        return int(years.max()) if not years.empty else 0

    def _normalize(self, indicator_rows: pd.DataFrame, class_name: str, question: str) -> pd.DataFrame:
        """
        Normalize raw BRFSS indicator rows to standard output format.

        Coerces numeric fields, renames columns, adds metadata.
        """
        # Coerce numeric fields
        indicator_rows["value"] = pd.to_numeric(indicator_rows.get("data_value"), errors="coerce")
        indicator_rows["low_ci"] = pd.to_numeric(indicator_rows.get("low_confidence_limit"), errors="coerce")
        indicator_rows["high_ci"] = pd.to_numeric(indicator_rows.get("high_confidence_limit"), errors="coerce")
        indicator_rows["sample_size"] = pd.to_numeric(indicator_rows.get("sample_size"), errors="coerce")

        # Drop rows with non-numeric values
        cleaned = indicator_rows[indicator_rows["value"].notna()].copy()

        # Rename columns
        cleaned = cleaned.rename(
            columns={
                "locationabbr": "state",
                "locationdesc": "state_name",
                "yearstart": "year",
            }
        )

        # Convert year to int
        cleaned["year"] = pd.to_numeric(cleaned["year"], errors="coerce").astype("Int64")

        # Add metadata
        cleaned["data_source"] = "CDC BRFSS hn4x-zwk7"
        cleaned["class_name"] = class_name
        cleaned["question"] = question

        # Final column order
        desired_cols = [
            "year",
            "state",
            "state_name",
            "value",
            "low_ci",
            "high_ci",
            "sample_size",
            "data_source",
            "class_name",
            "question",
        ]

        return cleaned[desired_cols].reset_index(drop=True)

    def _empty_indicator_df(self) -> pd.DataFrame:
        """Return empty DataFrame with standard indicator column structure."""
        return pd.DataFrame(
            columns=[
                "year",
                "state",
                "state_name",
                "value",
                "low_ci",
                "high_ci",
                "sample_size",
                "data_source",
                "class_name",
                "question",
            ]
        )

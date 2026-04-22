"""PopHealth Observatory core and NHANESExplorer implementation.

SPDX-License-Identifier: MIT
Copyright (c) 2025 Paul Boys and PopHealth Observatory contributors
"""

import warnings
from typing import Any

import pandas as pd
import requests  # noqa: F401 - retained for test patch compatibility

from .nhanes_analysis_service import (
    analyze_by_demographics as analyze_by_demographics_service,
)
from .nhanes_analysis_service import (
    create_demographic_visualization as create_demographic_visualization_service,
)
from .nhanes_analysis_service import (
    generate_summary_report as generate_summary_report_service,
)
from .nhanes_data_access import build_nhanes_xpt_url_patterns, try_download_xpt
from .nhanes_manifest_service import (
    build_detailed_component_manifest,
    classify_data_file,
    derive_local_filename,
    extract_size,
    fetch_component_page,
    normalize_year_span,
    parse_component_table,
)
from .nhanes_transforms import harmonize_blood_pressure, harmonize_body_measures, harmonize_demographics

warnings.filterwarnings("ignore")


class PopHealthObservatory:
    """Core observatory class for population health survey data (initial focus: NHANES)."""

    def __init__(self):
        # Primary cycle base for direct cycle folder structure (older & standard pattern)
        self.base_url = "https://wwwn.cdc.gov/Nchs/Nhanes"
        # Alternate base (newer public data file listing structure observed for recent cycles)
        self.alt_base_url = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"
        # In‑memory cache for downloaded component XPTs
        self.data_cache = {}  # cache: cycle_component -> DataFrame
        self.available_cycles = [
            "2021-2022",  # recent combined cycle (post-pandemic)
            "2019-2020",
            "2017-2018",
            "2015-2016",
            "2013-2014",
            "2011-2012",
            "2009-2010",
        ]
        # Map survey cycle to NHANES file letter suffix (partial set; extend as needed)
        self.cycle_suffix_map = {
            "2021-2022": "L",
            "2019-2020": "K",  # partial / limited release
            "2017-2018": "J",
            "2015-2016": "I",
            "2013-2014": "H",
            "2011-2012": "G",
            "2009-2010": "F",
            # Earlier examples (not currently in available_cycles):
            "2007-2008": "E",
            "2005-2006": "D",
            "2003-2004": "C",
            "2001-2002": "B",
            "1999-2000": "A",
        }
        self.components = {
            "demographics": "DEMO",
            "body_measures": "BMX",
            "blood_pressure": "BPX",
            "cholesterol": "TCHOL",
            "diabetes": "GLU",
            "dietary": "DR1TOT",
            "physical_activity": "PAQ",
            "smoking": "SMQ",
            "alcohol": "ALQ",
        }

    def get_data_url(self, cycle: str, component: str) -> str:
        """Return the best-guess URL for a given cycle/component.

        NHANES file naming convention pairs a survey cycle with a letter code (e.g., 2017-2018 -> J)
        Files then follow pattern: <COMPONENT>_<LETTER>.XPT inside a folder named by full cycle
        (older pattern) or under the newer public data path.
        """
        letter = self.cycle_suffix_map.get(cycle)
        if not letter:
            raise ValueError(f"No letter suffix mapping for cycle '{cycle}'. Update cycle_suffix_map.")
        # Candidate URL patterns (order matters). We'll try each until one works in download.
        candidates = [
            f"{self.base_url}/{cycle}/{component}_{letter}.XPT",  # standard
            # Some recent hosting patterns use year start folder and DataFiles subfolder
            f"{self.alt_base_url}/{cycle.split('-')[0]}/DataFiles/{component}_{letter}.xpt",  # alt lower-case ext
            f"{self.alt_base_url}/{cycle.split('-')[0]}/DataFiles/{component}_{letter}.XPT",  # alt upper-case ext
        ]
        # Return first candidate; download will iterate if needed (implemented there)
        return candidates[0]

    def download_data(self, cycle: str, component: str) -> pd.DataFrame:
        """Download data for a specific component and cycle with flexible URL handling.

        This method tries multiple URL patterns to handle the different formats used across NHANES cycles.
        """
        key = f"{cycle}_{component}"
        if key in self.data_cache:
            return self.data_cache[key]

        letter = self.cycle_suffix_map.get(cycle, "")
        url_patterns = build_nhanes_xpt_url_patterns(
            cycle=cycle,
            component=component,
            letter=letter,
            base_url=self.base_url,
            alt_base_url=self.alt_base_url,
        )

        df, success_url, errors = try_download_xpt(url_patterns, timeout_seconds=30)
        if df is not None and success_url is not None:
            print(f"✓ Success loading {component} from: {success_url}")
            self.data_cache[key] = df
            return df

        print(f"Failed to download {component} for {cycle}. Tried {len(url_patterns)} URLs.")
        print(f"Sample errors: {errors[:3]}")  # Show first 3 errors to avoid spam
        return pd.DataFrame()

    # Reuse logic from legacy NHANESExplorer below for compatibility


class NHANESExplorer(PopHealthObservatory):
    """NHANES-focused explorer extending :class:`PopHealthObservatory`.

    Provides:
    - Robust cycle/component XPT downloads (inherited)
    - Metadata table parsing producing rich manifest entries
    - Convenience analytic helpers (merging, summaries, visuals)
    - Manifest persistence with schema versioning & filtering
    """

    # Manifest schema tag for emitted artifacts.
    _MANIFEST_SCHEMA_VERSION = "1.0.0"

    def _normalize_year_span(self, year_text: str | None) -> str:
        """Normalize raw year span text into canonical YYYY_YYYY form."""
        return normalize_year_span(year_text)

    def _derive_local_filename(self, remote_url: str, year_norm: str) -> str | None:
        """Derive canonical local filename for an XPT file with year suffix."""
        return derive_local_filename(remote_url, year_norm)

    def _classify_data_file(self, href: str, label: str) -> str:
        """Classify file anchor into a coarse data type."""
        return classify_data_file(href, label)

    def _extract_size(self, label: str) -> str | None:
        """Extract human-readable size token from link label."""
        return extract_size(label)

    def _parse_component_table(self, html: str, page_url: str) -> list[dict[str, Any]]:
        """Parse component listing table into normalized dictionaries."""
        return parse_component_table(html, page_url)

    def _fetch_component_page(self, component_name: str) -> str | None:
        """Fetch component page HTML with simple multi-URL retry & cache."""
        if not hasattr(self, "_component_page_cache"):
            self._component_page_cache: dict[str, str] = {}
        return fetch_component_page(component_name, self._component_page_cache)

    def get_detailed_component_manifest(
        self,
        components: list[str] | None = None,
        as_dataframe: bool = False,
        year_range: tuple[str, str] | None = None,
        file_types: list[str] | None = None,
        force_refresh: bool = False,
        schema_version: str | None = None,
    ) -> dict[str, Any]:
        """Build enriched metadata manifest for selected component pages.

        Parameters
        ----------
        components : list[str] | None
            Subset of component pages among: Demographics, Examination, Laboratory, Dietary, Questionnaire.
            If None, all are attempted.
        as_dataframe : bool
            If True, attaches flattened DataFrame under key 'dataframe'.
        year_range : tuple[str,str] | None
            Inclusive start/end years; rows overlapping this span retained.
        file_types : list[str] | None
            Filter to only these data_file_type values (e.g. ['XPT','ZIP']).
        force_refresh : bool
            If True, bypass cached component page HTML.
        schema_version : str | None
            Override emitted schema version tag (advanced / experimental).

        Returns
        -------
        dict
            Manifest containing per-component records and summary counts.
            Top-level keys:
              - schema_version
              - generated_at (UTC ISO8601)
              - detailed_year_records (raw grouped rows)
              - summary_counts (nested counts by component and file type)
              - component_count
              - total_file_rows (post-filter)
        """
        if not hasattr(self, "_component_page_cache"):
            self._component_page_cache: dict[str, str] = {}

        return build_detailed_component_manifest(
            components=components,
            as_dataframe=as_dataframe,
            year_range=year_range,
            file_types=file_types,
            force_refresh=force_refresh,
            schema_version=schema_version or self._MANIFEST_SCHEMA_VERSION,
            cache=self._component_page_cache,
            fetch_page=self._fetch_component_page,
            parse_table=self._parse_component_table,
        )

    def save_detailed_component_manifest(self, path: str, **manifest_kwargs) -> str:
        """Generate and persist a detailed component manifest to JSON.

        Parameters
        ----------
        path : str
            Output JSON file path.
        **manifest_kwargs : Any
            Forwarded to ``get_detailed_component_manifest``.
        """
        manifest = self.get_detailed_component_manifest(**manifest_kwargs)
        try:
            import json

            with open(path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed writing manifest to {path}: {e}") from e
        return path

    def get_demographics_data(self, cycle: str = "2017-2018") -> pd.DataFrame:
        """Download demographics and delegate harmonization to transform helpers."""
        demo_df = self.download_data(cycle, self.components["demographics"])
        return harmonize_demographics(demo_df)

    def get_body_measures(self, cycle: str = "2017-2018") -> pd.DataFrame:
        """Download body measures and delegate harmonization to transform helpers."""
        bmx_df = self.download_data(cycle, self.components["body_measures"])
        return harmonize_body_measures(bmx_df)

    def get_blood_pressure(self, cycle: str = "2017-2018") -> pd.DataFrame:
        """Download blood pressure and delegate harmonization to transform helpers."""
        bp_df = self.download_data(cycle, self.components["blood_pressure"])
        return harmonize_blood_pressure(bp_df)

    def create_merged_dataset(self, cycle: str = "2017-2018") -> pd.DataFrame:
        """Merge DEMO, BMX, BPX slices on participant_id."""
        print(f"Creating merged dataset for {cycle}...")
        demo_df = self.get_demographics_data(cycle)
        body_df = self.get_body_measures(cycle)
        bp_df = self.get_blood_pressure(cycle)
        merged = demo_df.copy()
        if not body_df.empty:
            merged = merged.merge(body_df, on="participant_id", how="left")
        if not bp_df.empty:
            merged = merged.merge(bp_df, on="participant_id", how="left")
        print(f"Merged dataset created with {len(merged)} participants and {len(merged.columns)} variables")
        return merged

    def analyze_by_demographics(self, df: pd.DataFrame, metric: str, demographic: str) -> pd.DataFrame:
        """Group metric by demographic and compute standard descriptive stats."""
        return analyze_by_demographics_service(df, metric, demographic)

    def create_demographic_visualization(self, df: pd.DataFrame, metric: str, demographic: str):
        """Boxplot + mean bar chart for metric by demographic (if available)."""
        return create_demographic_visualization_service(df, metric, demographic)

    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """Generate textual summary of demographics & selected health metrics."""
        return generate_summary_report_service(df)

    def get_survey_weight(self, components: list[str]) -> str:
        """
        Determine the appropriate survey weight variable for given components.

        NHANES uses different sample weights depending on which components are analyzed.
        This method recommends the correct weight variable based on CDC guidelines.

        Parameters
        ----------
        components : list[str]
            List of component names being analyzed

        Returns
        -------
        str
            Recommended weight variable name (harmonized column name)

        Examples
        --------
        >>> explorer = NHANESExplorer()
        >>> weight = explorer.get_survey_weight(['demographics', 'body_measures'])
        >>> print(weight)  # 'exam_weight'
        >>> weight = explorer.get_survey_weight(['demographics'])
        >>> print(weight)  # 'interview_weight'

        Notes
        -----
        Weight selection hierarchy (per CDC guidelines):
        - Dietary data → dietary_day1_weight (most restrictive)
        - Laboratory/Examination data → exam_weight
        - Interview/Questionnaire only → interview_weight
        """
        # Check for dietary components (most restrictive weight)
        dietary_components = ["dietary"]
        if any(comp in components for comp in dietary_components):
            return "dietary_day1_weight"

        # Check for examination/laboratory components
        exam_components = ["body_measures", "blood_pressure", "laboratory"]
        if any(comp in components for comp in exam_components):
            return "exam_weight"

        # Default to interview weight for questionnaire-only analyses
        return "interview_weight"

    def calculate_weighted_mean(
        self, data: pd.DataFrame, variable: str, weight_var: str = None, min_weight: float = 0
    ) -> dict:
        """
        Calculate weighted mean of a variable using survey weights.

        Parameters
        ----------
        data : pd.DataFrame
            Dataset containing variable and weights
        variable : str
            Name of the variable to calculate mean for
        weight_var : str, optional
            Name of weight variable. If None, will auto-detect from data columns.
        min_weight : float, default=0
            Minimum weight value to include (exclude zero weights)

        Returns
        -------
        dict
            Dictionary with keys:
            - weighted_mean : float
            - unweighted_mean : float
            - n_obs : int (number of observations used)
            - sum_weights : float (total weight, for reference)

        Examples
        --------
        >>> explorer = NHANESExplorer()
        >>> data = explorer.create_merged_dataset('2017-2018')
        >>> result = explorer.calculate_weighted_mean(data, 'avg_systolic', 'exam_weight')
        >>> print(f"Weighted mean: {result['weighted_mean']:.2f}")
        """
        import numpy as np

        # Auto-detect weight variable if not provided
        if weight_var is None:
            weight_candidates = ["exam_weight", "interview_weight", "dietary_day1_weight"]
            for candidate in weight_candidates:
                if candidate in data.columns:
                    weight_var = candidate
                    print(f"Auto-detected weight variable: {weight_var}")
                    break

        if weight_var is None:
            raise ValueError("No weight variable found in data. Include weights in demographics data.")

        # Filter to valid observations
        valid_data = data[
            (data[variable].notna()) & (data[weight_var].notna()) & (data[weight_var] > min_weight)
        ].copy()

        if len(valid_data) == 0:
            raise ValueError(f"No valid observations for variable '{variable}' with weight '{weight_var}'")

        # Calculate weighted mean
        weighted_mean = np.average(valid_data[variable], weights=valid_data[weight_var])

        # Calculate unweighted mean for comparison
        unweighted_mean = valid_data[variable].mean()

        return {
            "weighted_mean": weighted_mean,
            "unweighted_mean": unweighted_mean,
            "n_obs": len(valid_data),
            "sum_weights": valid_data[weight_var].sum(),
            "variable": variable,
            "weight_var": weight_var,
        }

    def validate(self, cycle: str, components: list[str]) -> dict:
        """
        Validate downloaded NHANES data against official CDC metadata.

        Performs programmatic validation by comparing downloaded data against
        official CDC documentation, including URL correctness and row counts.

        Parameters
        ----------
        cycle : str
            NHANES cycle to validate (e.g., '2017-2018')
        components : list[str]
            List of component names to validate (e.g., ['demographics', 'body_measures'])

        Returns
        -------
        dict
            Validation report with overall status and component-level details.
            Structure: {
                'cycle': str,
                'status': str ('PASS'|'WARN'|'FAIL'),
                'components': {
                    component_name: {
                        'status': str,
                        'checks': {check_name: {status, details, expected, actual}}
                    }
                }
            }

        Examples
        --------
        >>> explorer = NHANESExplorer()
        >>> report = explorer.validate('2017-2018', ['demographics', 'body_measures'])
        >>> print(report['status'])  # 'PASS' or 'FAIL' or 'WARN'
        >>> print(report['components']['demographics']['checks']['row_count']['status'])
        """
        from .validation import run_validation

        validation_report = run_validation(self, cycle, components)
        return validation_report.to_dict()
